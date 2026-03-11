# Specialized Prompt Templates — 12 Category Scans

## Overview

Each template is designed to be injected as the `user` message in a Perplexity API call,
paired with the system prompt from `super-prompt.md`.

---

## Template 1: Reliability Audit

```
SCAN: reliability
SCOPE: memory/, core/, services/, orchestrators/
DEPTH: full

Detect:
1. Missing transaction boundaries — DB writes without BEGIN/COMMIT (ADR-0028 violation)
2. Race conditions — concurrent shared-state access without asyncio.Lock
3. Unhandled edge cases — no null/bounds checks on PacketEnvelope fields
4. Missing error recovery — external calls without try/except + circuit breaker (ADR-0009)
5. Resource leaks — connections/file handles opened without async context manager (ADR-0033)
6. DAG pipeline violations — validation outside intake_node (ADR-0012 violation)

L9-specific checks:
- PacketEnvelope.parent_ids accessed without length check
- SubstrateService methods missing transaction context
- Memory ingestion pipeline missing rollback on partial failure
- Kernel loader YAML parsing without schema validation (ADR-0030)

Output JSON findings array with code_before/code_after for each gap.
```

## Template 2: Security Audit

```
SCAN: security
SCOPE: api/, config/, core/governance/, services/, runtime/
DEPTH: full

Detect:
1. Hardcoded secrets — string literals containing keys/passwords (ADR-0038 violation)
2. SQL injection — string concatenation/f-strings in SQL queries
3. Missing authentication — FastAPI routes without dependency injection auth (ADR-0025)
4. Insufficient input validation — user input directly used in Cypher/SQL queries
5. Insecure deserialization — pickle.loads, yaml.load without SafeLoader
6. Missing RBAC checks — governance operations without authority hierarchy (ADR-0013)
7. Path traversal — file operations without sandboxed path resolution (ADR-0001)

L9-specific checks:
- API routes in api/routes/ missing Depends(verify_api_key)
- Neo4j Cypher queries with string interpolation (ADR-0032 violation)
- Kernel YAML files loaded with yaml.load instead of yaml.safe_load
- MCP memory endpoints without tenant isolation (ADR-0005)

Output JSON findings array with code_before/code_after for each gap.
```

## Template 3: Performance Audit

```
SCAN: performance
SCOPE: memory/, graph_adapter/, services/, orchestrators/
DEPTH: full

Detect:
1. N+1 queries — loops containing individual DB queries
2. Missing DB indexes — queries on unindexed columns in migrations/
3. Inefficient algorithms — O(n squared) nested loops over packets/embeddings
4. Memory leaks — unbounded caches without LRU eviction (ADR-0027 violation)
5. Blocking I/O in async — time.sleep(), synchronous requests in async functions
6. Missing connection pooling — new DB connections per request
7. Embedding batch inefficiency — single-item embedding calls vs batch (ADR-0029)

L9-specific checks:
- memory/semantic_search.py doing sequential embedding lookups
- graph_adapter/ creating new Neo4j sessions per query
- Orchestrator patterns doing sequential LLM calls that could be parallelized
- Redis operations in memory_cache/ without pipeline batching

Output JSON findings array with code_before/code_after for each gap.
```

## Template 4: Architecture Audit

```
SCAN: architecture
SCOPE: . (entire repo)
DEPTH: full

Detect:
1. God classes — files >500 lines or classes >50 methods
2. Circular dependencies — import cycles violating ADR-0002
3. SOLID violations — classes with multiple responsibilities
4. Missing abstraction layers — direct DB access from route handlers
5. Tight coupling — high fan-in/fan-out in dependency graph
6. Protocol violations — concrete types where Protocol should be used (ADR-0026)
7. Registry pattern violations — singletons not using auto-registry (ADR-0004/0022)

L9-specific checks:
- memory/ modules importing from api/ (layer violation)
- core/agents/executor.py doing work that belongs in orchestrators/
- Services not using FastAPI dependency injection (ADR-0025 violation)
- Tool definitions not following ADR-0017 schema
- Kernel configs not externalized per ADR-0053

Output JSON findings array with code_before/code_after for each gap.
```

## Template 5: Testing Audit

```
SCAN: testing
SCOPE: tests/, memory/, core/, api/
DEPTH: full

Detect:
1. Coverage gaps — critical modules without corresponding test files
2. Missing integration tests — only unit tests, no end-to-end DAG pipeline tests
3. Fixture violations — not following ADR-0020 test fixture hierarchy
4. Missing negative tests — only happy-path coverage
5. Flaky tests — tests depending on timing, external services, or ordering
6. Missing property-based tests for PacketEnvelope validation

L9-specific checks:
- No test file for memory/substrate_dag.py (critical path)
- Missing governance approval gate integration tests
- Kernel loader tests not covering malformed YAML
- No tests for circuit breaker behavior (ADR-0009)
- Missing WebSocket connection pattern tests (ADR-0031)

Output JSON findings array. For each gap, include a test skeleton.
```

## Template 6: Observability Audit

```
SCAN: observability
SCOPE: core/observability/, telemetry/, api/, memory/, services/
DEPTH: full

Detect:
1. Silent failures — except Exception: pass (or bare except)
2. Missing structlog calls — functions without log.info/warning/error (ADR-0019)
3. Standard logging usage — import logging or logging.getLogger (BANNED by ADR-0019)
4. Missing DORA metadata — modules without __dora_meta__ dict (ADR-0014 violation)
5. Missing health checks — services without /health endpoint
6. Missing metrics — critical operations without timing/counter instrumentation
7. Missing distributed tracing — async operations without trace context

L9-specific checks:
- Five-tier observability system completeness (core/observability/)
- Grafana dashboard coverage for all critical paths
- PacketEnvelope operations missing audit trail emission
- Memory DAG pipeline nodes missing span creation

Output JSON findings array with code_before/code_after for each gap.
```

## Template 7: Documentation Audit

```
SCAN: documentation
SCOPE: . (entire repo)
DEPTH: full

Detect:
1. Missing docstrings — public functions/classes without docstrings (ADR-0003)
2. Outdated READMEs — README files not matching current code
3. Missing ADR compliance — new patterns without corresponding ADR
4. Missing API docs — FastAPI routes without OpenAPI descriptions
5. Missing runbooks — critical operations without incident response docs
6. Missing architecture diagrams — complex subsystems without visual docs

Output JSON findings array with specific missing documentation items.
```

## Template 8: ADR Compliance Audit

```
SCAN: adr_compliance
SCOPE: . (entire repo)
DEPTH: full

For EACH of the 56 L9 ADRs (0000-0055), verify:
1. Is the pattern implemented where required?
2. Are there violations of the ADR rules?
3. Are there files that should follow the ADR but do not?

Priority ADRs:
- ADR-0002: TYPE_CHECKING imports in EVERY file with type-only imports
- ADR-0006: PacketEnvelope emitted for ALL data-mutating operations
- ADR-0012: Validation ONLY in intake_node, nowhere else in DAG
- ADR-0014: __dora_meta__ in EVERY Python module
- ADR-0019: structlog in EVERY file that logs (zero standard logging)
- ADR-0028: Transaction context for ALL database writes
- ADR-0038: Zero hardcoded secrets

Output: Per-ADR compliance score (0-100%) + specific violations as JSON.
```

## Template 9: Dependency Audit

```
SCAN: dependencies
SCOPE: requirements.txt, requirements-docker.txt, pyproject.toml
DEPTH: full

Detect:
1. Unpinned dependencies — packages without exact version pins
2. Known vulnerabilities — CVEs in current dependency versions
3. Unused dependencies — installed but never imported
4. Missing dependencies — imported but not in requirements
5. Incompatible versions — conflicting version constraints
6. License compliance — dependencies with incompatible licenses

Output JSON findings array with: package, current version, recommended version, CVE IDs.
```

## Template 10: Migration Audit

```
SCAN: migrations
SCOPE: migrations/
DEPTH: full

Detect:
1. Missing down migrations — migrations without rollback SQL
2. Data loss risk — destructive operations (DROP, TRUNCATE) without safety
3. Sequential apply violations — gaps in migration numbering (ADR-0015)
4. Missing indexes — tables created without appropriate indexes
5. Schema drift — migration state vs actual DB schema
6. Missing RLS policies — tables without row-level security (ADR-0005)

Output JSON findings array with SQL before/after for each gap.
```

## Template 11: CI/CD Pipeline Audit

```
SCAN: ci_cd
SCOPE: .github/workflows/, ci/, .pre-commit-config.yaml, Makefile
DEPTH: full

Detect:
1. Missing security scanning — no SAST/DAST in pipeline (ADR-0040)
2. Missing test gates — deployments without test pass requirements
3. Missing lint gates — PRs mergeable without ruff/mypy pass
4. Secrets in CI — hardcoded tokens in workflow files
5. Missing smoke tests — no post-deploy verification
6. Missing audit trail — deployments without logging

L9-specific checks:
- Pre-commit hooks covering ADR-0019 (structlog enforcement)
- Bandit security scanning configuration (.bandit)
- Semgrep rules (.semgrep/) covering L9-specific anti-patterns
- Gitleaks configuration (.gitleaks.toml) completeness

Output JSON findings array with workflow fix diffs.
```

## Template 12: Runtime Safety Audit

```
SCAN: runtime_safety
SCOPE: runtime/, core/governance/, private/kernels/
DEPTH: full

Detect:
1. Missing approval gates — high-risk operations without governance check (ADR-0013)
2. Missing circuit breakers — external service calls without resilience (ADR-0009)
3. Missing rate limiting — API endpoints without throttling
4. Kernel isolation violations — kernels accessing other kernel state directly
5. Feature flag gaps — new features not behind flags (ADR-0008)
6. Missing graceful degradation — single-point-of-failure components (ADR-0055)

L9-specific checks:
- Tool execution without capability scoping (ADR-0034)
- Agent operations without must_stay_async decorator (ADR-0010)
- Lazy initialization not used for expensive resources (ADR-0011)
- WebSocket connections without proper lifecycle management (ADR-0031)

Output JSON findings array with code_before/code_after for each gap.
```
