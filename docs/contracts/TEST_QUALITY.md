# TEST_QUALITY.md — Test Suite Quality Contract

<!-- L9-TEMPLATE: true -->
<!-- DOMAIN: universal -->
<!-- ENFORCED_BY: tools/auditors/test_quality.py -->

---

## What This Contract Prevents

False confidence from tests that exist but don't verify behavior.
Prevents Rule 9 (test harness must actually run) and Root Cause #7.

---

## Bug Classes

### A) Weak Test — HIGH
Test method with zero assertions. Runs but proves nothing.
**Fix:** Add assert/assertEqual/assertTrue.

### B) Empty Test File — HIGH
File named test_*.py with zero test_* functions.
**Fix:** Add tests or delete the file.

### C) Handler Untested — MEDIUM
Handler action exists but no test references it.
**Fix:** Create test file covering happy path + error path.

### D) Broken Fixture Path — HIGH
conftest.py uses relative path without __file__ anchor.
**Fix:** Use `Path(__file__).parent.parent / "domains"`
