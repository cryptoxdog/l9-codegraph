"""Compliance test for log safety auditor."""

import sys, pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def test_no_sensitive_data_in_logs():
    sys.path.insert(0, str(REPO_ROOT))
    from tools.auditors.log_safety import LogSafetyAuditor

    auditor = LogSafetyAuditor()
    files = auditor.scope.resolve(REPO_ROOT)
    if not files:
        pytest.skip("No engine/tools Python files to scan")
    result = auditor.scan(files, REPO_ROOT)
    high = [f for f in result.findings if f.severity == "HIGH"]
    assert not high, f"Sensitive data in logs ({len(high)}):\n" + "\n".join(
        f"  [{f.code}] {f.file}:{f.line}" for f in high
    )
