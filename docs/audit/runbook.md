# Operational Runbook — L9 Perplexity Audit Pipeline

## Running the Pipeline

### Full Audit (all 12 categories)
```bash
python scripts/perplexity_audit_agent.py --mode full
```
**Duration:** 15-45 minutes depending on repo size
**Output:** `reports/perplexity_audit/audit_YYYYMMDD_HHMMSS.{json,md}`

### Single Category Scan
```bash
python scripts/perplexity_audit_agent.py --mode category --category security --scope api/
```

### Incremental Scan (PR mode)
```bash
python scripts/perplexity_audit_agent.py --mode incremental --changed-files api/server.py memory/ingestion.py
```

## Interpreting Results

### Severity Guide
- **P0 (Red):** Stop everything. Fix immediately. These are data loss, security breach, or production crash risks.
- **P1 (Orange):** Schedule within current sprint. Functionality degradation or ADR violations.
- **P2 (Yellow):** Add to backlog. Tech debt that compounds over time.
- **P3 (Green):** Nice-to-have. Address during refactoring sprints.

### False Positives
If a finding is a false positive:
1. Add the pattern to `config/perplexity_audit.yaml` under `exclusions.patterns`
2. Document why in a comment
3. Track false positive rate per category

### Common Issues

**API rate limit exceeded:**
```
Symptom: "rate_limit_wait" logs appearing frequently
Fix: Reduce scan scope or increase rate_limit_rpm in config
```

**JSON parse failures:**
```
Symptom: "json_parse_failed" warnings in logs
Fix: Check Perplexity API status; consider reducing max_tokens
```

**No findings returned:**
```
Symptom: Empty findings array
Fix: Verify file content is being sent; check API key validity
```

## Maintenance

### Weekly
- Review false positive rate per category
- Check API usage against budget

### Monthly
- Update prompt templates based on new ADRs
- Review and tune severity classifications
- Check Perplexity model updates (sonar-pro improvements)

### Quarterly
- Full prompt optimization pass
- Benchmark against manual code review results
- Update ADR compliance matrix for new ADRs

## Emergency Procedures

### Pipeline Down
1. Check `PERPLEXITY_API_KEY` validity
2. Check Perplexity API status: https://status.perplexity.ai
3. Verify network connectivity from runner
4. Fall back to manual audit using `prompt-templates.md`

### P0 Finding in Production
1. Pipeline auto-creates GitHub issue with `P0` label
2. On-call engineer reviews within 1 hour
3. If confirmed: create hotfix branch, apply `code_after` patch
4. Run incremental audit on fix to verify resolution
5. Deploy with expedited review

## Metrics to Track

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| Debt Ratio | <5% | >10% |
| Gap Density | <0.5/kLOC | >1.0/kLOC |
| Fix Velocity | >10/sprint | <5/sprint |
| Regression Rate | <10% | >20% |
| False Positive Rate | <10% | >25% |
| P0 Count | 0 | >0 |
