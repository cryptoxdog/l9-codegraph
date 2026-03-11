# ADR Compliance Matrix

Maps each L9 ADR to automated audit checks performed by the pipeline.

## Foundation ADRs (0001-0013)

| ADR | Title | Audit Category | Check Description | Auto-Detectable |
|-----|-------|---------------|-------------------|-----------------|
| 0001 | Sandboxed Path Resolution | security | File operations use `Path.resolve()` with root check | Yes |
| 0002 | Circular Import Prevention | architecture | All type-only imports inside `TYPE_CHECKING` block | Yes |
| 0003 | Documentation Standards | documentation | Public functions/classes have docstrings | Yes |
| 0004 | Singleton Auto-Registry | architecture | Singletons use `@register` decorator pattern | Partial |
| 0005 | RLS Shared Tenant Model | security, migrations | Tables have RLS policies; queries include tenant filter | Partial |
| 0006 | PacketEnvelope Audit Trail | reliability, adr_compliance | Data-mutating ops emit PacketEnvelope | Partial |
| 0007 | 7-Phase Bootstrap | architecture | Bootstrap sequence follows phase ordering | Manual |
| 0008 | Feature Flag Gating | runtime_safety | New features behind feature flags | Partial |
| 0009 | Circuit Breaker Resilience | reliability, runtime_safety | External calls wrapped with circuit breaker | Yes |
| 0010 | must_stay_async Decorator | architecture | Async functions have `@must_stay_async` | Yes |
| 0011 | Lazy Initialization | performance | Expensive resources use lazy init pattern | Partial |
| 0012 | Memory DAG Pipeline | reliability, adr_compliance | Validation ONLY in `intake_node` | Yes |
| 0013 | Governance Authority | runtime_safety | High-risk ops check authority hierarchy | Partial |

## Core Pattern ADRs (0014-0023)

| ADR | Title | Audit Category | Check Description | Auto-Detectable |
|-----|-------|---------------|-------------------|-----------------|
| 0014 | DORA Metadata Block | observability, adr_compliance | Every `.py` has `__dora_meta__` dict | Yes |
| 0015 | Migration Sequential Apply | migrations | No gaps in migration numbering | Yes |
| 0016 | TypedDict vs Pydantic | architecture | Boundary: TypedDict internal, Pydantic at API edge | Partial |
| 0017 | Tool Definition Schema | architecture | Tool defs follow canonical schema | Yes |
| 0018 | Async Retry Pattern | reliability | Retries use async pattern with backoff | Yes |
| 0019 | structlog Logging | observability, adr_compliance | Zero `import logging` or `logging.getLogger` | Yes |
| 0020 | Test Fixture Hierarchy | testing | Fixtures follow session > module > function hierarchy | Partial |
| 0021 | LangGraph Node Wrapper | architecture | LangGraph nodes use wrapper pattern | Partial |
| 0022 | Registry Pattern | architecture | Registries use canonical pattern | Partial |
| 0023 | Error Packet Pattern | reliability | Errors wrapped in error packets | Partial |

## Advanced Pattern ADRs (0024-0040)

| ADR | Title | Audit Category | Check Description | Auto-Detectable |
|-----|-------|---------------|-------------------|-----------------|
| 0025 | FastAPI Dependency Injection | architecture, security | Routes use `Depends()` for auth/services | Yes |
| 0026 | Protocol-Based Abstractions | architecture | Abstract types use `Protocol` not ABC | Yes |
| 0027 | LRU Cache Pattern | performance | Caches use `@lru_cache` with maxsize | Yes |
| 0028 | Database Transaction Context | reliability | DB writes inside transaction context | Yes |
| 0029 | Embedding Generation Pipeline | performance | Embeddings use batch pipeline | Partial |
| 0030 | Kernel YAML Schema | reliability | YAML configs validated against schema | Partial |
| 0031 | WebSocket Connection | runtime_safety | WebSocket lifecycle properly managed | Partial |
| 0032 | Neo4j Cypher Query | security | No string interpolation in Cypher queries | Yes |
| 0033 | Async Context Manager | reliability | Resources use `async with` pattern | Yes |
| 0034 | Agent Capability Scoping | runtime_safety | Tool execution scoped to agent capabilities | Partial |
| 0035 | ADR Bootstrap Protocol | adr_compliance | AI agents read ADRs at session startup | Manual |
| 0036 | Schema Organization | architecture | Schemas follow canonical organization | Partial |
| 0037 | Tool Wiring Protocol | architecture | Tools wired via protocol, not hardcoded | Partial |
| 0038 | Secrets Management | security | Zero hardcoded secrets; all via env vars | Yes |
| 0039 | L9 CLI Tool | documentation | CLI commands documented | Manual |
| 0040 | CI/CD Security Scanning | ci_cd | SAST/DAST in pipeline | Yes |

## Detection Coverage

| Status | Count | Percentage |
|--------|-------|-----------|
| Fully Auto-Detectable | 22 | 40% |
| Partially Auto-Detectable | 20 | 36% |
| Manual Review Required | 4 | 7% |
| Proposed (not enforced) | 10 | 18% |

**Target:** Increase fully auto-detectable to >60% by Phase 4.
