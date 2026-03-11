# QUERY_PERFORMANCE.md — Query Performance Contract

<!-- L9-TEMPLATE: true -->
<!-- DOMAIN: universal -->
<!-- ENFORCED_BY: tools/auditors/query_performance.py -->

---

## What This Contract Prevents

N+1 query patterns, unbounded result sets, and Python repr in queries.

---

## Bug Classes

### A) N+1 Query — HIGH
Database call (.run(), .execute(), .search()) inside a for loop.
**Fix:** Batch queries outside loop or use UNWIND in Cypher.

### B) Unbounded Query — MEDIUM
Cypher MATCH with RETURN but no LIMIT.
**Fix:** Add `LIMIT $limit` parameter or use pagination.

### C) str() on Collection — HIGH (also Rule 5)
`str([list])` produces Python repr, not valid JSON/Cypher.
**Fix:** Use `json.dumps()` or pass as `$param`.
