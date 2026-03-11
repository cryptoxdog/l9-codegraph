# API_REGRESSION.md — Public API Backward Compatibility Contract

<!-- L9-TEMPLATE: true -->
<!-- DOMAIN: universal -->
<!-- ENFORCED_BY: tools/auditors/api_regression.py -->

---

## What This Contract Prevents

Breaking changes to public class/method signatures that crash downstream
callers. Directly prevents Rule 7 (constructor signature drift) and
Rule 8 (payload contract drift).

**Audit history:** H-12 — DomainPackLoader instantiated with wrong constructor
args because signature changed without updating callers.

---

## Bug Classes

### A) Class Removed — CRITICAL
Public class deleted entirely. Every caller that imports it crashes with ImportError.

### B) Method Removed — CRITICAL
Public method deleted. Callers get AttributeError.
**Fix:** Add deprecation shim that calls the replacement method.

### C) Signature Changed — HIGH
Method arguments renamed/reordered/removed. Callers pass wrong args.
**Fix:** Update METHODSIGNATURES.md FIRST, then grep + update ALL callers.

### D) Return Type Changed — HIGH
Return annotation changed. Callers expecting old type may crash.
**Fix:** Update RETURNVALUES.md + all callers.

---

## Enforcement

| Layer | Tool | When |
|---|---|---|
| CI | `audit_dispatch.py --auditor api_regression --strict` | Every PR |
| Pre-merge | `make audit-regression` | Before merge to main |

---

## Self-Check

After changing ANY public class or method:
1. Did you update `docs/contracts/METHODSIGNATURES.md`?
2. Did you `grep -rn "ClassName("` to find all callers?
3. Did you update all callers to match the new signature?
4. Run: `python tools/audit_dispatch.py --auditor api_regression`
