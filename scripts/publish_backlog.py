#!/usr/bin/env python3
"""Validate, render, and idempotently publish the BBMS GitHub backlog."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "backlog" / "issues.json"
REPOSITORY = "ANDYGAMER4321/SE_miniProject"
ASSIGNEE = "DukeAvi"
MARKER = re.compile(r"<!-- backlog-key: ([A-Z0-9-]+) -->")

MILESTONES = {
    1: {
        "title": "Sprint 1",
        "due_on": "2026-10-23T18:29:59Z",
        "description": "Sprint 1: 19 October 2026 to 23 October 2026",
    },
    2: {
        "title": "Sprint 2",
        "due_on": "2026-10-30T18:29:59Z",
        "description": "Sprint 2: 26 October 2026 to 30 October 2026",
    },
}

BASE_LABELS = {
    "type: implementation": ("1f6feb", "Functional implementation work"),
    "type: security": ("b60205", "Security implementation or validation"),
    "type: quality": ("5319e7", "Quality attribute or test work"),
    "type: decision": ("d4c5f9", "Decision required before dependent work"),
    "type: process": ("0e8a16", "Project workflow or delivery task"),
    "type: documentation": ("0075ca", "Documentation or contract work"),
    "type: bug": ("d73a4a", "Reproducible defect or regression"),
    "priority: high": ("b60205", "Must be completed or resolved first"),
    "priority: medium": ("fbca04", "Important after high-priority work"),
    "sprint: 1": ("c2e0c6", "Planned for Sprint 1"),
    "sprint: 2": ("bfd4f2", "Planned for Sprint 2"),
}

POINT_COLORS = {1: "ededed", 2: "d4c5f9", 3: "bfdadc", 5: "fbca04", 8: "f9d0c4"}
AREA_COLOR = "c5def5"


def gh(*args: str, input_text: str | None = None) -> str:
    process = subprocess.run(
        ["gh", *args],
        cwd=ROOT,
        input=input_text,
        text=True,
        capture_output=True,
    )
    if process.returncode:
        detail = process.stderr.strip() or process.stdout.strip()
        raise RuntimeError(f"gh {' '.join(args)} failed: {detail}")
    return process.stdout.strip()


def load_and_validate() -> list[dict]:
    with MANIFEST.open(encoding="utf-8") as handle:
        issues = json.load(handle)

    required = {
        "key",
        "title",
        "type",
        "priority",
        "sprint",
        "points",
        "module",
        "design",
        "test",
        "dependencies",
        "scope",
        "acceptance",
        "verification",
    }
    keys = [item.get("key") for item in issues]
    duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate backlog keys: {', '.join(duplicates)}")

    known = set(keys)
    for index, item in enumerate(issues, start=1):
        missing = sorted(required - set(item))
        if missing:
            raise ValueError(f"Item {index} is missing: {', '.join(missing)}")
        if not re.fullmatch(r"[A-Z0-9-]+", item["key"]):
            raise ValueError(f"Invalid key: {item['key']}")
        if item["type"] not in {"implementation", "security", "quality", "decision", "process", "documentation"}:
            raise ValueError(f"Invalid type for {item['key']}: {item['type']}")
        if item["priority"] not in {"high", "medium"}:
            raise ValueError(f"Invalid priority for {item['key']}: {item['priority']}")
        if item["sprint"] not in MILESTONES:
            raise ValueError(f"Invalid sprint for {item['key']}: {item['sprint']}")
        if item["points"] not in POINT_COLORS:
            raise ValueError(f"Invalid story points for {item['key']}: {item['points']}")
        unknown = sorted(set(item["dependencies"]) - known)
        if unknown:
            raise ValueError(f"Unknown dependencies for {item['key']}: {', '.join(unknown)}")
        if not item["acceptance"] or not item["verification"]:
            raise ValueError(f"Acceptance and verification are required for {item['key']}")
    return issues


def issue_labels(item: dict) -> list[str]:
    return [
        f"type: {item['type']}",
        f"priority: {item['priority']}",
        f"sprint: {item['sprint']}",
        f"points: {item['points']}",
        f"area: {item['module']}",
    ]


def dependency_lines(item: dict, numbers: dict[str, int]) -> list[str]:
    if not item["dependencies"]:
        return ["- None"]
    lines = []
    for dependency in item["dependencies"]:
        number = numbers.get(dependency)
        link = f"#{number}" if number else "not yet published"
        lines.append(f"- `{dependency}`: {link}")
    return lines


def render_body(item: dict, numbers: dict[str, int]) -> str:
    acceptance = "\n".join(f"- [ ] {criterion}" for criterion in item["acceptance"])
    verification = "\n".join(f"- [ ] {check}" for check in item["verification"])
    dependencies = "\n".join(dependency_lines(item, numbers))
    return f"""<!-- backlog-key: {item['key']} -->
## Outcome

{item['scope']}

## Planning

| Field | Value |
| --- | --- |
| Work item | `{item['key']}` |
| Design reference | `{item['design']}` |
| Verification reference | `{item['test']}` |
| Priority | {item['priority'].title()} |
| Sprint | Sprint {item['sprint']} |
| Story points | {item['points']} |

## Dependencies

{dependencies}

## Acceptance criteria

{acceptance}

## Verification

{verification}
- [ ] Record test commands, results, and sanitized evidence in the pull request.
- [ ] Update requirement-to-design-to-test traceability where this item changes it.

## Definition of done

- [ ] Acceptance criteria are satisfied.
- [ ] Relevant automated and manual checks pass.
- [ ] API, migration, configuration, and user documentation are current.
- [ ] No secret, personal, clinical, or production data is committed.
- [ ] A focused pull request links this issue and requests review from @{ASSIGNEE}.

## Source documents

- Blood Bank Management System SRS, latest copy in `dox/`
- BBMS Software Architecture and Design Specification, sections 3 and 4
- BBMS Software Test Plan
- Software Engineering Mini-Project Deliverables Part 2
"""


def render_index(issues: list[dict], output: Path) -> None:
    sprint_counts = Counter(item["sprint"] for item in issues)
    sprint_points = Counter()
    for item in issues:
        sprint_points[item["sprint"]] += item["points"]

    lines = [
        "# BBMS delivery backlog",
        "",
        "This index mirrors the GitHub issue backlog derived from the SRS, SAD, Software Test Plan, and Part-2 deliverables. The detailed acceptance and verification criteria live in `backlog/issues.json` and in the published issues.",
        "",
        "## Plan summary",
        "",
        "| Sprint | Dates | Items | Story points |",
        "| --- | --- | ---: | ---: |",
        f"| Sprint 1 | 19-23 October 2026 | {sprint_counts[1]} | {sprint_points[1]} |",
        f"| Sprint 2 | 26-30 October 2026 | {sprint_counts[2]} | {sprint_points[2]} |",
        f"| Total |  | {len(issues)} | {sum(item['points'] for item in issues)} |",
        "",
        "## Backlog",
        "",
        "| Key | Issue | Type | Priority | Sprint | Points | Dependencies |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for item in issues:
        dependencies = ", ".join(f"`{key}`" for key in item["dependencies"]) or "None"
        title = item["title"].replace("|", "\\|")
        lines.append(
            f"| `{item['key']}` | {title} | {item['type'].title()} | "
            f"{item['priority'].title()} | {item['sprint']} | {item['points']} | {dependencies} |"
        )
    lines.extend(
        [
            "",
            "## Working agreement",
            "",
            "Each issue is implemented on its own branch and merged only through a pull request reviewed by `@DukeAvi`. See `CONTRIBUTING.md` for branch naming, test evidence, review, and merge rules.",
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")


def existing_issue_numbers() -> dict[str, int]:
    payload = gh(
        "api",
        "--method",
        "GET",
        f"repos/{REPOSITORY}/issues?state=all&per_page=100",
    )
    numbers: dict[str, int] = {}
    for issue in json.loads(payload):
        match = MARKER.search(issue.get("body") or "")
        if match:
            numbers[match.group(1)] = issue["number"]
    return numbers


def backlog_issues() -> list[dict]:
    payload = gh(
        "api",
        "--method",
        "GET",
        f"repos/{REPOSITORY}/issues?state=all&per_page=100",
    )
    results = []
    for issue in json.loads(payload):
        match = MARKER.search(issue.get("body") or "")
        if match:
            issue["backlog_key"] = match.group(1)
            results.append(issue)
    return results


def all_repository_issues() -> list[dict]:
    payload = gh(
        "api",
        "--method",
        "GET",
        f"repos/{REPOSITORY}/issues?state=all&per_page=100",
    )
    return [issue for issue in json.loads(payload) if "pull_request" not in issue]


def delete_all_repository_issues() -> int:
    repository = json.loads(gh("api", f"repos/{REPOSITORY}"))
    if not repository.get("permissions", {}).get("admin"):
        raise RuntimeError("repository admin permission is required to permanently delete issues")
    issues = all_repository_issues()
    mutation = """
mutation($issueId: ID!) {
  deleteIssue(input: {issueId: $issueId}) {
    clientMutationId
  }
}
"""
    for issue in issues:
        gh(
            "api",
            "graphql",
            "-f",
            f"query={mutation}",
            "-F",
            f"issueId={issue['node_id']}",
        )
        print(f"deleted #{issue['number']} {issue['title']}", flush=True)
    return len(issues)


def delete_assigned_backlog_issues(known_keys: set[str]) -> int:
    assigned = [
        issue
        for issue in backlog_issues()
        if issue["backlog_key"] in known_keys and issue.get("assignees")
    ]
    mutation = """
mutation($issueId: ID!) {
  deleteIssue(input: {issueId: $issueId}) {
    clientMutationId
  }
}
"""
    for issue in assigned:
        gh(
            "api",
            "graphql",
            "-f",
            f"query={mutation}",
            "-F",
            f"issueId={issue['node_id']}",
        )
        print(f"deleted #{issue['number']} {issue['backlog_key']} (was assigned)", flush=True)
    return len(assigned)


def retire_assigned_backlog_issues(known_keys: set[str]) -> dict[str, dict]:
    assigned = [
        issue
        for issue in backlog_issues()
        if issue["backlog_key"] in known_keys and issue.get("assignees")
    ]
    retired = {}
    for issue in assigned:
        key = issue["backlog_key"]
        original_body = issue.get("body") or ""
        retired_body = original_body.replace(
            f"<!-- backlog-key: {key} -->",
            f"<!-- retired-backlog-key: {key} -->",
            1,
        )
        notice = (
            "> This assigned copy was retired before work began. "
            "An unassigned replacement will be linked after publication.\n\n"
        )
        gh(
            "api",
            "--method",
            "PATCH",
            f"repos/{REPOSITORY}/issues/{issue['number']}",
            "--input",
            "-",
            input_text=json.dumps(
                {
                    "title": f"[Retired assigned copy] {issue['title']}",
                    "body": notice + retired_body,
                    "state": "closed",
                    "state_reason": "not_planned",
                    "assignees": [],
                }
            ),
        )
        retired[key] = {"number": issue["number"], "body": retired_body}
        print(f"retired #{issue['number']} {key} (assignment cleared)", flush=True)
    return retired


def prepare_assigned_recreation(known_keys: set[str]) -> dict[str, dict]:
    repository = json.loads(gh("api", f"repos/{REPOSITORY}"))
    if repository.get("permissions", {}).get("admin"):
        removed = delete_assigned_backlog_issues(known_keys)
        print(f"Permanently removed {removed} assigned backlog issues.", flush=True)
        return {}
    retired = retire_assigned_backlog_issues(known_keys)
    print(
        f"Retired {len(retired)} assigned issues because permanent deletion requires repository-owner access.",
        flush=True,
    )
    return retired


def link_retired_issues(retired: dict[str, dict], numbers: dict[str, int]) -> None:
    for key, issue in retired.items():
        replacement = numbers[key]
        notice = (
            f"> This assigned copy was retired before work began. "
            f"Continue in the unassigned replacement: #{replacement}.\n\n"
        )
        gh(
            "api",
            "--method",
            "PATCH",
            f"repos/{REPOSITORY}/issues/{issue['number']}",
            "--input",
            "-",
            input_text=json.dumps(
                {
                    "body": notice + issue["body"],
                    "state": "closed",
                    "state_reason": "not_planned",
                    "assignees": [],
                }
            ),
        )


def ensure_labels(issues: list[dict]) -> None:
    definitions = dict(BASE_LABELS)
    for item in issues:
        definitions[f"points: {item['points']}"] = (
            POINT_COLORS[item["points"]],
            f"Estimated at {item['points']} story point{'s' if item['points'] != 1 else ''}",
        )
        definitions[f"area: {item['module']}"] = (
            AREA_COLOR,
            f"Work in the {item['module']} area",
        )
    for name, (color, description) in sorted(definitions.items()):
        gh(
            "label",
            "create",
            name,
            "--repo",
            REPOSITORY,
            "--color",
            color,
            "--description",
            description,
            "--force",
        )


def ensure_milestones() -> None:
    payload = gh(
        "api",
        "--method",
        "GET",
        f"repos/{REPOSITORY}/milestones?state=all&per_page=100",
    )
    existing = {item["title"] for item in json.loads(payload)}
    for milestone in MILESTONES.values():
        if milestone["title"] in existing:
            continue
        gh(
            "api",
            "--method",
            "POST",
            f"repos/{REPOSITORY}/milestones",
            "-f",
            f"title={milestone['title']}",
            "-f",
            f"description={milestone['description']}",
            "-f",
            f"due_on={milestone['due_on']}",
        )


def publish(issues: list[dict]) -> dict[str, int]:
    gh("auth", "status", "--hostname", "github.com")
    ensure_labels(issues)
    ensure_milestones()
    numbers = existing_issue_numbers()

    for item in issues:
        if item["key"] in numbers:
            print(f"exists  #{numbers[item['key']]} {item['key']}")
            continue
        args = [
            "issue",
            "create",
            "--repo",
            REPOSITORY,
            "--title",
            f"{item['key']}: {item['title']}",
            "--body",
            render_body(item, numbers),
            "--milestone",
            MILESTONES[item["sprint"]]["title"],
        ]
        for label in issue_labels(item):
            args.extend(["--label", label])
        url = gh(*args)
        number = int(url.rstrip("/").rsplit("/", 1)[-1])
        numbers[item["key"]] = number
        print(f"created #{number} {item['key']}", flush=True)

    for item in issues:
        number = numbers[item["key"]]
        args = [
            "issue",
            "edit",
            str(number),
            "--repo",
            REPOSITORY,
            "--title",
            f"{item['key']}: {item['title']}",
            "--body",
            render_body(item, numbers),
            "--milestone",
            MILESTONES[item["sprint"]]["title"],
        ]
        for label in issue_labels(item):
            args.extend(["--add-label", label])
        gh(*args)
        print(f"synced  #{number} {item['key']} (unassigned)", flush=True)

    print(f"Published and synchronized {len(issues)} issues in {REPOSITORY}.")
    return numbers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="create or synchronize GitHub issues")
    parser.add_argument(
        "--recreate-assigned",
        action="store_true",
        help="permanently delete assigned managed issues before recreating them unassigned",
    )
    parser.add_argument(
        "--purge-existing",
        action="store_true",
        help="permanently delete every existing repository issue before publishing",
    )
    parser.add_argument(
        "--render-index",
        metavar="PATH",
        help="write the human-readable backlog index relative to the repository root",
    )
    args = parser.parse_args()

    try:
        issues = load_and_validate()
        if args.render_index:
            output = (ROOT / args.render_index).resolve()
            if ROOT not in output.parents:
                raise ValueError("The rendered index must stay inside the repository")
            render_index(issues, output)
            print(f"Rendered {len(issues)} backlog items to {output.relative_to(ROOT)}.")
        if args.apply:
            retired = {}
            if args.purge_existing:
                removed = delete_all_repository_issues()
                print(f"Permanently removed all {removed} existing repository issues.", flush=True)
            elif args.recreate_assigned:
                retired = prepare_assigned_recreation({item["key"] for item in issues})
            numbers = publish(issues)
            if retired:
                link_retired_issues(retired, numbers)
                print(f"Linked {len(retired)} retired copies to their unassigned replacements.", flush=True)
        elif not args.render_index:
            counts = Counter(item["sprint"] for item in issues)
            points = Counter()
            for item in issues:
                points[item["sprint"]] += item["points"]
            print(f"Validated {len(issues)} backlog items for {REPOSITORY}.")
            for sprint in sorted(counts):
                print(f"Sprint {sprint}: {counts[sprint]} items, {points[sprint]} story points")
            print("No GitHub changes made. Use --apply to publish.")
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
