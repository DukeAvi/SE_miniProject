"""Run the full npm audit, excluding one advisory withdrawn by GitHub."""

import json
import subprocess
import sys
from pathlib import Path

# Withdrawn 2026-11-18; npm still serves it. Remove when npm drops the entry.
# https://github.com/advisories/GHSA-fc5q-39xc-vjpf
WITHDRAWN = "https://github.com/advisories/GHSA-fc5q-39xc-vjpf"


def blocking_findings(report):
    if report.get("error") or report.get("auditReportVersion") != 2:
        raise ValueError("npm audit did not return a valid version 2 report")
    findings = report.get("vulnerabilities")
    if not isinstance(findings, dict):
        raise ValueError("npm audit report is missing vulnerability data")

    def withdrawn_only(name, seen):
        if name in seen or name not in findings:
            return False
        finding = findings[name]
        if not isinstance(finding, dict):
            return False
        causes = finding.get("via")
        if not isinstance(causes, list) or not causes:
            return False
        return all(
            withdrawn_only(cause, seen | {name}) if isinstance(cause, str)
            else isinstance(cause, dict)
            and cause.get("name") == "picomatch"
            and cause.get("url") == WITHDRAWN
            for cause in causes
        )

    return sorted(name for name in findings if not withdrawn_only(name, set()))


def main():
    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            cwd=Path(__file__).resolve().parents[1] / "frontend",
            capture_output=True, text=True, timeout=180, check=False,
        )
        report = json.loads(result.stdout)
        if result.returncode not in (0, 1):
            raise ValueError("npm audit command failed")
        blockers = blocking_findings(report)
        if result.returncode == 1 and not report["vulnerabilities"]:
            raise ValueError("npm audit failed without vulnerability findings")
    except (OSError, subprocess.TimeoutExpired, ValueError, AttributeError) as error:
        print(f"Dependency audit failed: {error}", file=sys.stderr)
        return 1
    if blockers:
        print("Dependency audit failed: " + ", ".join(blockers), file=sys.stderr)
        return 1
    count = len(report["vulnerabilities"])
    if count:
        print(f"Excluded {count} propagated findings for withdrawn advisory {WITHDRAWN}")
    print("Dependency audit passed: no active advisory findings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
