# GitHub backlog project

The [BBMS Backlog and Sprints project](https://github.com/users/DukeAvi/projects/1) is linked to `DukeAvi/SE_miniProject`. It contains all 49 work items from `backlog/issues.json`.

## Views

- **Backlog** is a table of open issues (`is:issue -status:Done`).
- **Sprint 1** is a board filtered to the Sprint 1 milestone.
- **Sprint 2** is a board filtered to the Sprint 2 milestone.

Each view displays Title, Status, Priority, Story Points, Assignees, Dependency Status, Dependencies, and Sprint. The project also retains the synchronized Labels and Milestone fields.

## Planning fields

Priority, sprint, and points mirror the issue labels and manifest. Dependencies lists prerequisite issue numbers and keys. Dependency Status is **Blocked** while any prerequisite remains open, **Ready** when all prerequisites are closed, and **None** when there are no prerequisites. Status is **Done** for closed issues, **In Progress** for assigned open issues, and **Todo** for unassigned open issues.

The manifest and linked issue bodies are the planning source of truth. Verify their correspondence with the project using:

```text
python scripts/audit_project_board.py
```

The audit requires GitHub CLI authentication with Project read access and write access to the Project. It checks repository linkage, the manifest-to-issue-to-project count and keys, planning labels and milestones, every populated project planning field, dependency state, view names, filters, layouts, and visible columns.
