# 🏆 Golden Repo — L9 Microservice Template

> The reference implementation for all L9 constellation services.
> Fork this. Fill in `.env`. Ship.

## Stack
- **Runtime:** FastAPI + Uvicorn (Python 3.11)
- **Packaging:** Poetry
- **Container:** Docker + Compose
- **CI:** Ruff, MyPy, Semgrep, SonarCloud, GitGuardian
- **Review:** CodeRabbit + Copilot
- **Toolbox:** Venture Forge Toolbox (16 DevOps scripts)

## Quick Start

### New service from this template
1. Click **"Use this template"** on GitHub
2. `cp .env.template .env.local` → fill in `APP_NAME`, `APP_API_KEY`
3. Update `sonar-project.properties` → set `sonar.projectKey`
4. `docker compose up --build`

### Local dev (no Docker)
```bash
poetry install
cp .env.template .env.local
tools/dev/dev_up.sh
```

## Project Structure
```
golden-repo/
├── engine/              ← Your service logic here
│   ├── main.py          ← FastAPI app + /health + /v1/execute
│   └── settings.py      ← Pydantic settings (reads .env)
├── tests/
│   ├── unit/
│   └── integration/
├── tools/               ← Venture Forge Toolbox (never edit)
├── .github/workflows/   ← CI quality gate + release drafter
├── .semgrep/            ← 8 Python security rules
├── templates/           ← .env, styleguide, dev.conf templates
├── sonar-project.properties
├── pyproject.toml       ← Poetry deps
├── Dockerfile           ← Dev image
├── Dockerfile.prod      ← Production image (non-root user)
└── docker-compose.yml   ← Local dev stack
```

## API Contract
```
POST /v1/execute
{
  "action": "match|sync|health|enrich",
  "tenant": "<tenant_id>",
  "payload": {}
}
```

## Toolbox Commands
```bash
tools/infra/check_env.sh          # Validate .env
tools/infra/docker_validate.sh    # Validate Dockerfiles + compose
tools/infra/test_everything.sh    # Full 11-section test suite
tools/infra/deep_mri.sh           # VPS diagnostics
tools/deploy/deploy.sh            # Deploy to VPS
```

## CI Secrets Required
| Secret | Source |
|--------|--------|
| `SONAR_TOKEN` | sonarcloud.io/account/security |
| `GITGUARDIAN_API_KEY` | dashboard.gitguardian.com/api |

## CI Variables Required
| Variable | Value |
|----------|-------|
| `PYTHON_VERSION` | `3.11` |
| `SONAR_PROJECT_KEY` | `cryptoxdog_YOUR-REPO` |
| `SONAR_ORG` | `cryptoxdog` |

## CI/CD Workflows

All active workflows in `.github/workflows/`:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | push / PR | Base lint (ruff, mypy), audit engine (27 rules), pytest, contract verification |
| `ci-quality.yml` | push / PR | Quality gates — shellcheck, bandit, ruff, SonarCloud |
| `perplexity-audit.yml` | schedule | Automated tech debt audit via Perplexity API |
| `sbom.yml` | push / PR / release | Software Bill of Materials generation (CycloneDX JSON + XML) |
| `secret-rotation-reminder.yml` | quarterly cron | Opens a GitHub Issue checklist for rotating all secrets |
| `slsa-build.yml` | version tags | SLSA Build Level 3 provenance + attestation via GHCR |
| `dependency-review.yml` | PR to main | Blocks PRs with moderate+ CVEs or disallowed licenses |
| `release-drafter.yml` | push to main / PR | Auto-drafts release notes from PR labels |

---
*Part of the L9 Constellation — [venture-forge-toolbox](https://github.com/cryptoxdog/venture-forge-toolbox)*
