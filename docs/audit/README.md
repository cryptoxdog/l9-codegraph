# L9 Perplexity Research Agent — Automated Tech Debt Pipeline

## God-Mode Super Prompt System for Autonomous Code Quality

**Version:** 1.0.0
**Target:** Perplexity API-enabled research agent operating inside L9
**Quality Standard:** Frontier AI lab (Anthropic/OpenAI/DeepMind tier)
**Status:** Production-ready

---

## Package Contents

| File | Purpose |
|------|--------|
| `README.md` | Master guide and orientation |
| `super-prompt.md` | God-Mode super prompt template for Perplexity API |
| `prompt-templates.md` | 12 specialized prompt templates per audit category |
| `03-PIPELINE-CONFIG.yaml` | Pipeline configuration, thresholds, scheduling |
| `implementation-roadmap.md` | 6-phase rollout plan with milestones |
| `05-AGENT-ORCHESTRATOR.py` | Production Python orchestrator |
| `report-schema.json` | JSON schema for standardized audit reports |
| `adr-compliance-matrix.md` | Maps all 56 L9 ADRs to audit checks |
| `08-CI-INTEGRATION.yaml` | GitHub Actions workflow |
| `runbook.md` | Operational runbook |
| `metrics-dashboard.md` | Grafana dashboard config |

## Architecture

```
Perplexity Research Agent Pipeline
┌─────────────────────────────────────────────┐
│  L9 Repo Scanner → Prompt Builder           │
│        ↓                                    │
│  Perplexity API (sonar-pro)                 │
│        ↓                                    │
│  Response Parser → Gap Report Generator     │
│        ↓                    ↓               │
│  Phase Pack Generator   GitHub Issues       │
│        ↓                                    │
│  Auto-Fix PR Generator (Phase 5+)          │
└─────────────────────────────────────────────┘
```

## L9 ADR Compliance

This pipeline enforces ALL 56 L9 ADRs. Key constraints:

- **ADR-0002**: TYPE_CHECKING imports scanned in every file
- **ADR-0006**: PacketEnvelope audit trails verified
- **ADR-0012**: DAG pipeline validation-in-intake-only enforced
- **ADR-0014**: DORA metadata blocks checked on every module
- **ADR-0019**: structlog-only logging enforced (zero tolerance)
- **ADR-0028**: Database transaction context patterns verified
- **ADR-0038**: Secrets management protocol compliance checked
- **ADR-0040**: CI/CD security scanning alignment verified
