# Implementation Roadmap — 6-Phase Rollout

## Timeline Overview

| Phase | Name | Duration | Risk Tier | Key Deliverable |
|-------|------|----------|-----------|-----------------|
| 0 | Foundation | Week 1 | T1 | Single-category scan working locally |
| 1 | Full Coverage | Week 2 | T1 | All 12 categories operational |
| 2 | Report & GitHub Integration | Week 3 | T2 | Auto-reports + GitHub issues |
| 3 | CI/CD Integration | Week 4 | T2 | Automated PR checks + daily scans |
| 4 | Metrics & Dashboard | Week 5-6 | T1 | Grafana dashboard + alerts |
| 5 | Auto-Remediation | Week 7-8 | T3 | Auto-fix PRs with HITL gate |

---

## Phase 0: Foundation (Week 1)

**Objective:** Pipeline running locally with a single category scan.

### Tasks
1. Create `config/perplexity_audit.yaml` from `03-PIPELINE-CONFIG.yaml`
2. Add `PERPLEXITY_API_KEY` to `.env.example` and `.env`
3. Deploy `05-AGENT-ORCHESTRATOR.py` to `scripts/perplexity_audit_agent.py`
4. Add `httpx` to `requirements.txt` (verify; it may already be present)
5. Run first scan: `python scripts/perplexity_audit_agent.py --mode category --category security`
6. Verify JSON output in `reports/perplexity_audit/`

### Exit Criteria
- [ ] Single-category scan completes without errors
- [ ] JSON report is valid and contains findings
- [ ] No hardcoded secrets in pipeline code itself
- [ ] structlog used throughout (no standard logging)
- [ ] `__dora_meta__` block present in orchestrator module

### Risk Tier: T1 (read-only analysis, no repo modifications)

---

## Phase 1: Full Category Coverage (Week 2)

**Objective:** All 12 scan categories operational with quality output.

### Tasks
1. Test each of the 12 prompt templates against real L9 code
2. Tune temperature/max_tokens per category based on output quality
3. Implement robust JSON response parser with fallback strategies
4. Add retry logic with exponential backoff (ADR-0018 pattern)
5. Implement rate limiting (20 RPM for Perplexity API)
6. Run full audit: `python scripts/perplexity_audit_agent.py --mode full`
7. Measure and document false positive rate per category

### Exit Criteria
- [ ] All 12 categories produce valid findings
- [ ] Rate limiting prevents API throttling
- [ ] Full audit completes within 30 minutes
- [ ] False positive rate documented per category
- [ ] JSON output validates against `report-schema.json`

### Risk Tier: T1 (read-only analysis)

---

## Phase 2: Report Generation & GitHub Integration (Week 3)

**Objective:** Automated reports and GitHub issue creation for critical findings.

### Tasks
1. Implement markdown report generator from JSON findings
2. Implement GitHub issue auto-creation for P0/P1 findings via GitHub API
3. Implement phase pack generator (groups related findings into fix batches)
4. Add severity trend tracking (compare current vs previous audit)
5. Create PR template for audit-generated fixes
6. Test GitHub issue creation with dry-run mode

### Exit Criteria
- [ ] Markdown report generated alongside JSON for every audit
- [ ] P0 findings auto-create GitHub issues with `tech-debt`, `P0` labels
- [ ] Phase packs generated for P0/P1 findings with README + checklist
- [ ] Trend comparison works between two consecutive audits
- [ ] Dry-run mode tested before enabling live issue creation

### Risk Tier: T2 (creates GitHub issues — reversible by closing)

---

## Phase 3: CI/CD Integration (Week 4)

**Objective:** Pipeline runs automatically on PRs and daily schedule.

### Tasks
1. Deploy `08-CI-INTEGRATION.yaml` to `.github/workflows/perplexity-audit.yaml`
2. Configure incremental scans on PR (changed `.py` files only)
3. Configure daily full scans on main branch at 02:00 UTC
4. Add P0 finding as PR check (blocks merge)
5. Add PR comment with audit summary
6. Set `PERPLEXITY_API_KEY` as GitHub Actions secret
7. Test with a sample PR before enabling on all PRs

### Exit Criteria
- [ ] PR check runs incremental audit on every PR touching `.py` files
- [ ] Daily full audit runs at 02:00 UTC via cron schedule
- [ ] P0 findings block PR merge (exit code 1)
- [ ] PR comments posted with audit summary
- [ ] Audit artifacts uploaded for every run

### Risk Tier: T2 (blocks PRs — reversible by config change or workflow disable)

---

## Phase 4: Metrics & Dashboard (Week 5-6)

**Objective:** Full observability into tech debt trends.

### Tasks
1. Implement Prometheus metrics endpoint in the orchestrator
2. Deploy Grafana dashboard from `metrics-dashboard.md`
3. Track: gap count, fix velocity, debt ratio, regression rate
4. Set up alerts: P0 count >0, debt ratio >10%, regression rate >20%
5. Implement weekly automated report generation
6. Add metrics to existing L9 observability stack (core/observability/)

### Exit Criteria
- [ ] Grafana dashboard shows real-time debt metrics
- [ ] Alerts fire correctly on threshold breach
- [ ] Weekly report generated automatically
- [ ] Metrics integrated with L9 five-tier observability system

### Risk Tier: T1 (monitoring and reporting only)

---

## Phase 5: Auto-Remediation (Week 7-8)

**Objective:** Pipeline generates and submits fix PRs for lower-severity findings.

### Tasks
1. Implement code transformation engine (applies `code_after` patches)
2. Create branch per phase pack: `auto-fix/phase-{n}-{category}`
3. Generate PR with findings context, fix rationale, and test additions
4. Request Copilot code review on auto-generated PRs
5. Require human approval for ALL auto-generated PRs (mandatory HITL gate)
6. Implement rollback procedure for rejected auto-fixes

### Exit Criteria
- [ ] Auto-fix PRs created for P2/P3 findings only (P0/P1 remain human-driven)
- [ ] Each PR includes test additions or modifications
- [ ] Copilot review requested on every auto-fix PR
- [ ] Human approval required before merge (no auto-merge)
- [ ] Rollback procedure documented and tested

### Risk Tier: T3 (creates PRs with code changes — requires explicit approval per PR)

---

## Phase 6: Continuous Improvement (Ongoing)

**Objective:** Pipeline self-improves based on feedback and evolving ADRs.

### Tasks
1. Track false positive rate per category; target <10%
2. Refine prompts based on false positive patterns
3. Add new ADR compliance checks as ADRs are created (currently 56)
4. Quarterly prompt review and optimization
5. Benchmark against manual code review results
6. Evaluate model upgrades (sonar-pro improvements)

### Exit Criteria
- [ ] False positive rate <10% per category
- [ ] New ADRs auto-integrated within 1 sprint of creation
- [ ] Quarterly benchmark shows improvement over previous quarter
- [ ] Pipeline documentation stays current with repo changes

### Risk Tier: T1 (analysis and tuning)

---

## Budget Estimate

| Phase | Perplexity API Cost | Engineering Hours | Total |
|-------|-------------------|------------------|-------|
| 0 | ~$5 | 4h | 4h + $5 |
| 1 | ~$20 | 8h | 8h + $20 |
| 2 | ~$10 | 8h | 8h + $10 |
| 3 | ~$5 | 6h | 6h + $5 |
| 4 | ~$0 | 8h | 8h |
| 5 | ~$15 | 12h | 12h + $15 |
| **Total** | **~$55/month** | **46h** | **46h + $55** |

Monthly ongoing cost: ~$55-100 Perplexity API (daily full audits + PR incremental scans)
