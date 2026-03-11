"""Compliance test for API regression auditor."""

import subprocess, sys, pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def _has_git():
    r = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True, cwd=REPO_ROOT)
    return r.returncode == 0


@pytest.mark.skipif(not _has_git(), reason="No git repo")
def test_api_regression_no_critical():
    sys.path.insert(0, str(REPO_ROOT))
    from tools.auditors.api_regression import APIRegressionAuditor

    auditor = APIRegressionAuditor()
    files = auditor.scope.resolve(REPO_ROOT)
    result = auditor.scan(files, REPO_ROOT)
    critical = [f for f in result.findings if f.severity == "CRITICAL"]
    assert not critical, f"CRITICAL API regressions ({len(critical)}):\n" + "\n".join(
        f"  [{f.code}] {f.message}" for f in critical
    )
