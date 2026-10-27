# BBMS backlog source

`issues.json` is the reviewed source for the GitHub backlog. Every item has a stable key, sprint, story-point estimate, priority, dependencies, acceptance criteria, and verification expectations derived from the SRS, SAD, Software Test Plan, and Part-2 deliverables in `dox/`.

Run the validation and preview before publishing:

```bash
python3 scripts/publish_backlog.py
```

Publish only after GitHub CLI authentication is active:

```bash
python3 scripts/publish_backlog.py --apply
```

Publication is idempotent. The stable key embedded in each issue prevents duplicates if a run is interrupted. The publisher leaves every issue unassigned, creates the two documented sprint milestones, and adds planning labels. It does not commit or push repository files.
