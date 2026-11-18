# Frontend dependency audit

Issue #191 follows up the audit failure in main CI run 44340527627.

The 14 reported findings share one root cause: picomatch advisory
[GHSA-fc5q-39xc-vjpf](https://github.com/advisories/GHSA-fc5q-39xc-vjpf).
GitHub withdrew it on 18 November 2026. npm still serves the advisory, including
against the latest published release, 4.0.7. Its suggested ESLint downgrade does
not supply a patched picomatch release.

Run the same full dependency audit as CI from the repository root:

```sh
python scripts/audit_frontend_dependencies.py
```

The check runs `npm audit --json` and excludes only that withdrawn advisory and
parent findings caused exclusively by it. Other advisories, including new ones
against picomatch, remain failures regardless of severity. Registry errors,
invalid reports, and unknown dependency chains also fail. The check prints the
withdrawn advisory URL and excluded count, rather than claiming a clean raw npm
report. No dependencies or audit thresholds changed.

Remove this compatibility check and restore plain `npm audit` once npm stops
reporting the withdrawn entry. Raw `cd frontend && npm audit` remains useful for
inspecting registry data and may fail until then.
