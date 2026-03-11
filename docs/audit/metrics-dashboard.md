# Grafana Dashboard Configuration — L9 Tech Debt Metrics

## Dashboard UID: l9-tech-debt

### Panel 1: Total Findings Over Time (Time Series)

```json
{
  "title": "Total Findings Over Time",
  "type": "timeseries",
  "datasource": "Prometheus",
  "targets": [
    {
      "expr": "l9_audit_findings_total",
      "legendFormat": "Total"
    },
    {
      "expr": "l9_audit_findings_total{severity=\"P0\"}",
      "legendFormat": "P0 (Critical)"
    },
    {
      "expr": "l9_audit_findings_total{severity=\"P1\"}",
      "legendFormat": "P1 (High)"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "color": {"mode": "palette-classic"},
      "thresholds": {
        "steps": [
          {"color": "green", "value": 0},
          {"color": "yellow", "value": 50},
          {"color": "red", "value": 100}
        ]
      }
    }
  }
}
```

### Panel 2: Severity Distribution (Pie Chart)

```json
{
  "title": "Severity Distribution",
  "type": "piechart",
  "datasource": "Prometheus",
  "targets": [
    {"expr": "l9_audit_findings_total{severity=\"P0\"}", "legendFormat": "P0"},
    {"expr": "l9_audit_findings_total{severity=\"P1\"}", "legendFormat": "P1"},
    {"expr": "l9_audit_findings_total{severity=\"P2\"}", "legendFormat": "P2"},
    {"expr": "l9_audit_findings_total{severity=\"P3\"}", "legendFormat": "P3"}
  ]
}
```

### Panel 3: Debt Ratio Gauge

```json
{
  "title": "Technical Debt Ratio",
  "type": "gauge",
  "datasource": "Prometheus",
  "targets": [
    {"expr": "l9_audit_debt_ratio"}
  ],
  "fieldConfig": {
    "defaults": {
      "min": 0, "max": 100,
      "thresholds": {
        "steps": [
          {"color": "green", "value": 0},
          {"color": "yellow", "value": 5},
          {"color": "red", "value": 10}
        ]
      },
      "unit": "percent"
    }
  }
}
```

### Panel 4: Fix Velocity (Bar Chart)

```json
{
  "title": "Fix Velocity (Findings Closed per Sprint)",
  "type": "barchart",
  "datasource": "Prometheus",
  "targets": [
    {"expr": "increase(l9_audit_findings_closed_total[7d])", "legendFormat": "Closed"}
  ]
}
```

### Panel 5: Category Breakdown (Table)

```json
{
  "title": "Findings by Category",
  "type": "table",
  "datasource": "Prometheus",
  "targets": [
    {"expr": "l9_audit_findings_total", "legendFormat": "{{category}}"}
  ]
}
```

### Panel 6: Regression Rate (Stat)

```json
{
  "title": "Regression Rate",
  "type": "stat",
  "datasource": "Prometheus",
  "targets": [
    {
      "expr": "rate(l9_audit_findings_new_total[7d]) / rate(l9_audit_findings_closed_total[7d]) * 100"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "thresholds": {
        "steps": [
          {"color": "green", "value": 0},
          {"color": "yellow", "value": 10},
          {"color": "red", "value": 20}
        ]
      },
      "unit": "percent"
    }
  }
}
```

## Prometheus Metrics (Exposed by Pipeline)

| Metric | Type | Description |
|--------|------|-------------|
| `l9_audit_findings_total` | Gauge | Current total findings by severity and category |
| `l9_audit_findings_new_total` | Counter | New findings discovered |
| `l9_audit_findings_closed_total` | Counter | Findings resolved |
| `l9_audit_debt_ratio` | Gauge | Technical debt ratio percentage |
| `l9_audit_scan_duration_seconds` | Histogram | Audit scan duration |
| `l9_audit_api_calls_total` | Counter | Perplexity API calls made |
| `l9_audit_false_positive_total` | Counter | Findings marked as false positive |

## Alert Rules

```yaml
groups:
  - name: l9-tech-debt-alerts
    rules:
      - alert: P0FindingDetected
        expr: l9_audit_findings_total{severity="P0"} > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "P0 audit finding detected"

      - alert: HighDebtRatio
        expr: l9_audit_debt_ratio > 10
        for: 24h
        labels:
          severity: warning
        annotations:
          summary: "Technical debt ratio exceeds 10%"

      - alert: HighRegressionRate
        expr: >
          rate(l9_audit_findings_new_total[7d]) /
          rate(l9_audit_findings_closed_total[7d]) > 0.2
        for: 7d
        labels:
          severity: warning
        annotations:
          summary: "Regression rate exceeds 20%"
```
