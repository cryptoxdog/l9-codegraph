"""Compliance test for test quality auditor."""
import sys, pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent

def test_no_weak_tests():
    sys.path.insert(0, str(REPO_ROOT))
    from tools.auditors.test_quality import TestQualityAuditor
    auditor = TestQualityAuditor()
    files = auditor.scope.resolve(REPO_ROOT)
    result = auditor.scan(files, REPO_ROOT)
    weak = [f for f in result.findings if f.category == "WEAK_TEST"]
    assert not weak, (
        f"Weak tests ({len(weak)}):\n"
        + "\n".join(f"  [{f.code}] {f.file}:{f.line}" for f in weak))

def test_no_broken_fixtures():
    sys.path.insert(0, str(REPO_ROOT))
    from tools.auditors.test_quality import TestQualityAuditor
    auditor = TestQualityAuditor()
    files = auditor.scope.resolve(REPO_ROOT)
    result = auditor.scan(files, REPO_ROOT)
    broken = [f for f in result.findings if f.category == "FIXTURE_BROKEN"]
    assert not broken, (
        f"Broken fixtures ({len(broken)}):\n"
        + "\n".join(f"  [{f.code}] {f.file}:{f.line}" for f in broken))
