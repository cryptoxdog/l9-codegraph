# LOG_SAFETY.md — Sensitive Data Logging Prevention Contract

<!-- L9-TEMPLATE: true -->
<!-- DOMAIN: universal -->
<!-- ENFORCED_BY: tools/auditors/log_safety.py -->

---

## What This Contract Prevents

Sensitive data (passwords, tokens, API keys) leaking into log files,
stdout, or error responses visible to end users.

---

## Bug Classes

### A) Sensitive Data Logged — HIGH
Banned tokens in logger calls: password, secret, api_key, token, etc.

### B) Credential in Print — HIGH
Same tokens in print() statements.

### C) Stack Trace Leak — MEDIUM
`str(exception)` in user-facing response exposes file paths, SQL, etc.
**Fix:** Generic error message to user; log full exception internally.

---

## Banned Tokens

`password`, `passwd`, `secret`, `api_key`, `apikey`, `token`,
`access_token`, `refresh_token`, `private_key`, `credit_card`, `ssn`,
`neo4j_password`, `pg_password`, `db_password`
