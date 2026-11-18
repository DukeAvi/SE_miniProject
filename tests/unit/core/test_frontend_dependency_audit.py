import json
from subprocess import CompletedProcess

import pytest

from scripts.audit_frontend_dependencies import WITHDRAWN, blocking_findings, main


def report(findings):
    return {"auditReportVersion": 2, "vulnerabilities": findings}


def test_clean_report_passes():
    assert blocking_findings(report({})) == []


def test_withdrawn_advisory_and_transitive_parents_pass():
    findings = {
        "picomatch": {"via": [{"name": "picomatch", "url": WITHDRAWN}]},
        "micromatch": {"via": ["picomatch"]},
        "fast-glob": {"via": ["micromatch"]},
    }
    assert blocking_findings(report(findings)) == []


def test_new_advisory_in_same_package_still_blocks_parents():
    findings = {
        "picomatch": {"via": [
            {"name": "picomatch", "url": WITHDRAWN},
            {"name": "picomatch", "url": "https://github.com/advisories/GHSA-new"},
        ]},
        "micromatch": {"via": ["picomatch"]},
    }
    assert blocking_findings(report(findings)) == ["micromatch", "picomatch"]


@pytest.mark.parametrize("finding", [
    {"via": ["missing"]}, {"via": ["pkg"]}, {"via": []},
    {"via": [{"name": "other", "url": WITHDRAWN}]}, None,
])
def test_unknown_or_malformed_findings_block(finding):
    assert blocking_findings(report({"pkg": finding})) == ["pkg"]


@pytest.mark.parametrize("data", [{}, {"error": "registry unavailable"},
                                       {"auditReportVersion": 2}])
def test_invalid_report_fails(data):
    with pytest.raises(ValueError):
        blocking_findings(data)


@pytest.mark.parametrize("code, output, expected", [
    (0, report({}), 0),
    (1, report({"picomatch": {"via": [{"name": "picomatch", "url": WITHDRAWN}]}}), 0),
    (1, report({"other": {"via": [{"name": "other", "url": "new"}]}}), 1),
    (1, report({}), 1), (2, report({}), 1), (1, {"error": "offline"}, 1),
])
def test_command_exit_status(monkeypatch, code, output, expected):
    monkeypatch.setattr("scripts.audit_frontend_dependencies.subprocess.run",
                        lambda *args, **kwargs: CompletedProcess([], code, json.dumps(output)))
    assert main() == expected
