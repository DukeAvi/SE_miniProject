"""Verify the linked GitHub Project against the published backlog manifest."""

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OWNER = "DukeAvi"
REPOSITORY = "DukeAvi/SE_miniProject"
PROJECT_NUMBER = "1"
BACKLOG_PATH = ROOT / "backlog" / "issues.json"
REQUIRED_COLUMNS = {
    "Status",
    "Priority",
    "Story Points",
    "Assignees",
    "Dependency Status",
    "Dependencies",
    "Sprint",
}


def gh_json(*args):
    result = subprocess.run(
        ["gh", *args], check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def require(condition, message):
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def issue_key(issue):
    match = re.search(r"<!-- backlog-key: ([A-Z0-9-]+) -->", issue.get("body") or "")
    return match.group(1) if match else None


def project_values(project_id, items_by_key):
    fragment = (
        "content { ... on Issue { number title state } } "
        "fieldValues(first:25) { nodes { "
        "... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2SingleSelectField { name } } } "
        "... on ProjectV2ItemFieldNumberValue { number field { ... on ProjectV2Field { name } } } "
        "... on ProjectV2ItemFieldTextValue { text field { ... on ProjectV2Field { name } } } "
        "} }"
    )
    pairs = list(items_by_key.items())
    records = {}
    for offset in range(0, len(pairs), 6):
        batch = pairs[offset : offset + 6]
        selections = " ".join(
            f"i{index}:node(id:{json.dumps(item_id)})"
            f"{{... on ProjectV2Item{{{fragment}}}}}"
            for index, (_, item_id) in enumerate(batch)
        )
        response = gh_json("api", "graphql", "-f", f"query=query{{{selections}}}")
        require(not response.get("errors"), f"GraphQL audit failed: {response.get('errors')}")
        data = response["data"]
        for index, (key, _) in enumerate(batch):
            node = data[f"i{index}"]
            values = {}
            for value in node["fieldValues"]["nodes"]:
                field = (value.get("field") or {}).get("name")
                if field:
                    values[field] = value.get("name", value.get("number", value.get("text")))
            records[key] = {"issue": node["content"], "fields": values}
    return records


def main():
    manifest = json.loads(BACKLOG_PATH.read_text())
    rows = {row["key"]: row for row in manifest}
    require(len(rows) == len(manifest), "duplicate work-item keys in backlog/issues.json")

    issues = gh_json(
        "issue", "list", "--repo", REPOSITORY, "--state", "all", "--limit", "100",
        "--json", "number,title,body,state,labels,milestone,assignees",
    )
    issues_by_key = {issue_key(issue): issue for issue in issues if issue_key(issue)}
    require(set(rows) == set(issues_by_key), "backlog manifest and issue keys do not match")

    for key, row in rows.items():
        issue = issues_by_key[key]
        labels = {label["name"] for label in issue["labels"]}
        required_labels = {
            f"points: {row['points']}",
            f"priority: {row['priority']}",
            f"sprint: {row['sprint']}",
        }
        require(required_labels <= labels, f"{key}: missing planning labels {required_labels-labels}")
        require(
            issue.get("milestone", {}).get("title") == f"Sprint {row['sprint']}",
            f"{key}: milestone does not match sprint {row['sprint']}",
        )

    project = gh_json("project", "view", PROJECT_NUMBER, "--owner", OWNER, "--format", "json")
    project_id = project["id"]
    project_items = gh_json(
        "project", "item-list", PROJECT_NUMBER, "--owner", OWNER, "--limit", "100", "--format", "json"
    )["items"]
    require(len(project_items) == len(rows), f"expected {len(rows)} items, found {len(project_items)}")
    items_by_key = {
        issue_key(item.get("content", {})): item["id"]
        for item in project_items
        if issue_key(item.get("content", {}))
    }
    require(set(rows) == set(items_by_key), "backlog manifest and Project items do not match")

    repo_query = (
        f'query{{node(id:{json.dumps(project_id)})'
        "{... on ProjectV2 { repositories(first:100) { nodes { nameWithOwner } } }}}"
    )
    repo_data = gh_json("api", "graphql", "-f", f"query={repo_query}")
    linked_repositories = {
        node["nameWithOwner"]
        for node in repo_data["data"]["node"]["repositories"]["nodes"]
    }
    require(REPOSITORY in linked_repositories, f"Project is not linked to {REPOSITORY}")

    records = project_values(project_id, items_by_key)
    states = {key: record["issue"]["state"] for key, record in records.items()}
    for key, row in rows.items():
        issue = records[key]["issue"]
        values = records[key]["fields"]
        dependency_keys = row.get("dependencies", [])
        dependency_text = ", ".join(
            f"#{issues_by_key[dependency]['number']} ({dependency})"
            for dependency in dependency_keys
        ) or "None"
        dependency_status = (
            "None" if not dependency_keys
            else "Blocked" if any(states[item] != "CLOSED" for item in dependency_keys)
            else "Ready"
        )
        item = next(item for item in project_items if item["id"] == items_by_key[key])
        expected_status = (
            "Done" if issue["state"] == "CLOSED"
            else "In Progress" if item.get("assignees")
            else "Todo"
        )
        expected = {
            "Priority": row["priority"].title(),
            "Sprint": f"Sprint {row['sprint']}",
            "Story Points": float(row["points"]),
            "Dependencies": dependency_text,
            "Dependency Status": dependency_status,
            "Status": expected_status,
        }
        for field, value in expected.items():
            require(values.get(field) == value, f"{key}: {field} is {values.get(field)!r}, expected {value!r}")

    views_query = f'''query {{
      node(id:{json.dumps(project_id)}) {{
        ... on ProjectV2 {{
          views(first:20) {{
            nodes {{
              name layout filter
              fields(first:30) {{
                nodes {{
                  __typename
                  ... on ProjectV2Field {{ name }}
                  ... on ProjectV2SingleSelectField {{ name }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}'''
    views_data = gh_json("api", "graphql", "-f", f"query={views_query}")
    views = views_data["data"]["node"]["views"]["nodes"]
    expected_views = {
        "Backlog": ("TABLE_LAYOUT", "is:issue -status:Done"),
        "Sprint 1": ("BOARD_LAYOUT", 'milestone:"Sprint 1"'),
        "Sprint 2": ("BOARD_LAYOUT", 'milestone:"Sprint 2"'),
    }
    require({view["name"] for view in views} == set(expected_views), "view names do not match the expected three views")
    for view in views:
        require(
            (view["layout"], view["filter"]) == expected_views[view["name"]],
            f"{view['name']}: unexpected layout or filter",
        )
        visible = {field["name"] for field in view["fields"]["nodes"]}
        require(REQUIRED_COLUMNS <= visible, f"{view['name']}: missing columns {REQUIRED_COLUMNS-visible}")

    print(
        f"PASS: {len(rows)} manifest items match {len(items_by_key)} GitHub issues and Project items; "
        f"planning fields, dependencies, milestone labels, repository link, and {len(views)} views verified."
    )


if __name__ == "__main__":
    main()
