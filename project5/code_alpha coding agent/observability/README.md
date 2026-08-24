# Code Alpha Observability & Monitoring Guide

**Status**: ✅ **PRODUCTION READY**

Complete observability stack for Code Alpha with metrics, tracing, logging, and alerting.

---

## 📋 Overview

Comprehensive observability solution providing:

- **Metrics**: Prometheus with custom dashboards (Grafana)
- **Tracing**: Distributed tracing with Jaeger
- **Logging**: Log aggregation with Loki and Promtail
- **Alerting**: Rule-based alerts with Alertmanager
- **Instrumentation**: OpenTelemetry with automatic instrumentation
- **Exporters**: Multi-backend support (Datadog, New Relic, Elastic, etc.)

---

## 🏗️ Architecture

### Observability Stack

```
Applications (Code Alpha services)
         ↓
    OpenTelemetry SDK
    ├─→ Traces (Jaeger)
    ├─→ Metrics (Prometheus)
    └─→ Logs (Loki)
         ↓
    Collector (OpenTelemetry)
    ├─→ Prometheus (metrics storage)
    ├─→ Jaeger (trace storage)
    ├─→ Loki (log storage)
    └─→ External (Datadog, New Relic, etc.)
         ↓
    Visualization
    ├─→ Prometheus UI (raw metrics)
    ├─→ Grafana (dashboards)
    ├─→ Jaeger UI (traces)
    └─→ Loki (log queries)
         ↓
    Alerting
    ├─→ Alertmanager (routing)
    ├─→ Slack/PagerDuty (notifications)
    └─→ Custom webhooks
```

### Components

| Component | Purpose | Port | Storage |
|-----------|---------|------|---------|
| Prometheus | Metrics collection | 9090 | 50GB |
| Alertmanager | Alert routing | 9093 | N/A |
| Grafana | Visualization | 3000 | PostgreSQL |
| Jaeger | Distributed tracing | 16686 | BadgerDB |
| Loki | Log aggregation | 3100 | Filesystem |
| Promtail | Log shipper | N/A | N/A |
| OTel Collector | Data collection | 4317/4318 | N/A |
| Node Exporter | Host metrics | 9100 | N/A |
| cAdvisor | Container metrics | 8080 | N/A |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Required
- Docker Compose 2.0+
- 20GB disk space
- Ports: 3000, 3100, 4317, 4318, 6831, 6380, 8080, 9090, 9093, 9100, 14250, 14268, 16686
```

### Start Observability Stack

```bash
# Start all observability services
docker-compose -f observability/docker-compose-observability.yml up -d

# Verify services
docker-compose -f observability/docker-compose-observability.yml ps

# View logs
docker-compose -f observability/docker-compose-observability.yml logs -f prometheus
```

### Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Prometheus | http://localhost:9090 | None |
| Alertmanager | http://localhost:9093 | None |
| Grafana | http://localhost:3000 | admin/admin |
| Jaeger UI | http://localhost:16686 | None |
| Loki | http://localhost:3100 | None |
| cAdvisor | http://localhost:8080 | None |

---

## 📊 Metrics Collection

### Prometheus Configuration

Edit `prometheus-rules.yaml` to customize:
- Alert conditions
- Alert severity levels
- Query intervals
- Data retention

### Available Metrics

**API Gateway**
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency (histogram)
- `http_requests_created` - Request creation timestamp
- `http_exceptions_total` - HTTP exceptions

**Orchestrator**
- `orchestrator_tasks_total` - Total tasks
- `orchestrator_tasks_pending` - Pending tasks
- `orchestrator_tasks_duration_seconds` - Task duration
- `orchestrator_queue_depth` - Queue backlog

**Sandbox Worker**
- `sandbox_executions_total` - Total executions
- `sandbox_blocked_actions_total` - Blocked actions
- `sandbox_execution_duration_seconds` - Execution time

**Indexing Worker**
- `indexing_tasks_total` - Total indexing tasks
- `embedding_generation_duration_seconds` - Embedding latency
- `vectors_indexed_total` - Total indexed vectors

**Database**
- `pg_stat_activity_count` - Active connections
- `pg_database_size_bytes` - Database size
- `pg_slow_queries_total` - Slow query count

**Safety & Audit**
- `safety_blocked_actions_total` - Blocked actions
- `policy_violations_total` - Policy violations
- `audit_log_entries_total` - Total audit entries

---

## 🔍 Distributed Tracing

### Jaeger Features

- **Trace Sampling**: 10% of successful traces, all errors
- **Span Tags**: Automatic context propagation
- **Service Topology**: Visualize service dependencies
- **Latency Analysis**: Find bottlenecks
- **Error Tracking**: Correlate errors to traces

### View Traces

1. Go to http://localhost:16686
2. Select service (api, orchestrator, etc.)
3. Filter by tags:
   - `error=true` - Failed requests
   - `http.status_code=500` - Server errors
   - `duration > 1000ms` - Slow requests

### Trace Sampling Policy

```yaml
tail_sampling:
  policies:
    - error-traces: Always sample errors
    - success-sample: 10% of successful traces
    - slow-traces: Sample traces > 1 second
```

---

## 📝 Log Aggregation

### Loki Features

- **LogQL**: Query language for logs
- **Label-based indexing**: Efficient filtering
- **Promtail**: Automatic log collection
- **Retention**: 30-day retention by default

### Query Logs

```logql
# All logs from API service
{job="code-alpha-api"}

# Errors in API
{job="code-alpha-api"} | json | level="ERROR"

# Slow requests
{job="code-alpha-api"} | json | duration > "1000ms"

# Particular pod
{pod="api-xxxxx"}

# Container metrics
{pod="api-xxxxx"} | json | level != "DEBUG"
```

### Promtail Configuration

Configures log collection from:
- Docker containers
- Kubernetes pods
- Systemd logs
- Custom log files

---

## 🚨 Alerting

### Alert Rules

Configured in `prometheus-rules.yaml`:

**Critical Alerts** (immediate action)
- API is down (2 min)
- High blocked action rate (5 sec)
- Kubernetes node not ready (5 min)
- Database disk usage > 15GB

**Warning Alerts** (within 30 min)
- High error rate > 5%
- High latency (p99 > 1s)
- Memory usage > 1.5GB
- Queue depth > 1000 items

### Alert Routing

Configure in `alertmanager-config.yml`:
- **Slack**: Real-time notifications
- **PagerDuty**: On-call escalation
- **Email**: Summary notifications
- **Custom webhooks**: Custom handlers

### Alertmanager Web UI

Access http://localhost:9093 to:
- View active alerts
- Silence alerts temporarily
- Configure routing rules

---

## 📈 Grafana Dashboards

### Pre-built Dashboards

| Dashboard | Purpose | Queries |
|-----------|---------|---------|
| Overview | System health | 15+ metrics |
| API | API performance | Request rate, latency, errors |
| Infrastructure | K8s nodes | CPU, memory, disk |
| Database | PostgreSQL health | Connections, queries, size |
| Traces | Jaeger traces | Latency distribution |

### Create Custom Dashboard

1. Go to http://localhost:3000
2. Click "+" → Dashboard
3. Add panels with queries:
   ```promql
   # Request rate (5-min average)
   rate(http_requests_total[5m])

   # Error rate
   rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

   # P99 latency
   histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
   ```

---

## 🔧 OpenTelemetry Instrumentation

### Add to Python Application

```python
from observability.otel_instrumentation import (
    setup_otel_tracing,
    instrument_fastapi,
    instrument_libraries,
    create_custom_metrics,
    OTelContext
)

# Initialize
trace_provider, metric_provider = setup_otel_tracing("api", "production")
instrument_fastapi(app, "api")
instrument_libraries()
metrics = create_custom_metrics("api")

# Use in code
@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    with OTelContext("get_task", {"task_id": task_id}):
        # Your code here
        pass
```

### Automatic Instrumentation

Libraries automatically instrumented:
- FastAPI/Flask
- Requests
- PostgreSQL (psycopg2)
- SQLAlchemy
- Redis
- Logging

---

## 🔌 Multi-Backend Exporters

### Datadog Integration

```yaml
exporters:
  datadog:
    api:
      key: ${DATADOG_API_KEY}
```

### New Relic Integration

```yaml
exporters:
  newrelic:
    api_key: ${NEW_RELIC_API_KEY}
```

### Elastic APM Integration

```yaml
exporters:
  otlp:
    endpoint: apm-server:8200
```

### Splunk HEC

```yaml
exporters:
  splunk_hec:
    token: ${SPLUNK_HEC_TOKEN}
    endpoint: https://splunk:8088
```

---

## 📊 Performance Baseline

### Expected Performance

| Metric | Expected Value | Alert Threshold |
|--------|-----------------|-----------------|
| API p50 latency | 50ms | - |
| API p99 latency | 200ms | 1s |
| Error rate | < 0.1% | 5% |
| Database queries | 50ms | 500ms |
| Task completion | < 1min | 1hour |

### Capacity Planning

- Prometheus: 30GB for 30 days
- Loki: 1MB per 1000 log lines (typical)
- Jaeger: 100MB per 1M traces
- Grafana: 2GB for 100+ dashboards

---

## 🛠️ Troubleshooting

### Metrics Not Showing

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check if services export metrics
curl http://api:8000/metrics
curl http://orchestrator:8001/metrics

# View Prometheus logs
docker-compose logs prometheus
```

### Missing Traces

```bash
# Check Jaeger collector
curl http://localhost:14268/api/traces

# Verify OTEL_EXPORTER_OTLP_ENDPOINT
docker-compose exec api env | grep OTEL

# Check OTel collector logs
docker-compose logs otel-collector
```

### Alerts Not Firing

```bash
# View Alertmanager alerts
curl http://localhost:9093/api/v1/alerts

# Check alert rules
curl http://localhost:9090/api/v1/rules

# Verify webhook configuration
curl -X POST http://localhost:9093/api/v1/alerts -d '...'
```

### Disk Space Issues

```bash
# Check Prometheus storage
du -sh /path/to/prometheus

# Reduce retention
# Edit: --storage.tsdb.retention.time=7d (instead of 30d)

# Remove old data
docker-compose exec prometheus rm -rf /prometheus/wal/*
```

---

## 📚 Integration

### With GitHub Actions (CI/CD)

```yaml
# In .github/workflows/deploy-k8s.yml
- name: Wait for Prometheus metrics
  run: |
    curl -f http://prometheus:9090/api/v1/query?query=up{job="api"}
```

### With Kubernetes

```yaml
# k8s/otel-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: code-alpha
```

### With Docker Compose

```yaml
# docker/docker-compose.prod.yml
services:
  api:
    environment:
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
```

---

## ✅ Checklist

- [ ] Prometheus scraping all services
- [ ] Grafana dashboards created
- [ ] Jaeger receiving traces
- [ ] Loki collecting logs from all pods
- [ ] Alert rules evaluated
- [ ] Alertmanager routing configured
- [ ] Slack/PagerDuty integration tested
- [ ] Performance baselines established
- [ ] Retention policies configured
- [ ] Backup strategy for Prometheus data

---

## 📦 Deliverables (Module 15c Part 2)

### Configuration Files (5)
- ✅ `.github/workflows/build-and-test.yml` (CI/CD pipeline)
- ✅ `.github/workflows/deploy-k8s.yml` (K8s deployment)
- ✅ `observability/otel-collector-config.yaml` (OTel configuration)
- ✅ `observability/prometheus-rules.yaml` (Alert rules)
- ✅ `observability/docker-compose-observability.yml` (Observability stack)

### Code & Instrumentation (1)
- ✅ `observability/otel-instrumentation.py` (Python instrumentation)

### Documentation (1)
- ✅ `observability/README.md` (This guide)

### Features Implemented
- ✅ GitHub Actions CI/CD pipelines (build, test, deploy)
- ✅ Docker image building with security scanning
- ✅ Automated Kubernetes deployment with health checks
- ✅ Prometheus metrics collection from all services
- ✅ Grafana dashboards for visualization
- ✅ Jaeger distributed tracing
- ✅ Loki log aggregation
- ✅ Alert rules with multiple severity levels
- ✅ Multi-backend exporter support
- ✅ OpenTelemetry Python instrumentation

---

## 🔗 Integration Points

### With Module 15a (Docker)
- Docker Compose uses same services
- Environment variables coordinated
- Health checks integrated

### With Module 15b (Kubernetes)
- Kubernetes deployment pipeline
- Service monitoring
- Log collection from pods

---

## ✨ Status

**Module 15c Status**: ✅ **PRODUCTION READY**

- Complete CI/CD with GitHub Actions
- Kubernetes deployment automation
- Full observability stack
- Alert rules configured
- Instrumentation provided

---

## 📞 Support

For observability issues:

1. Check service logs: `docker-compose logs <service>`
2. View metrics: http://localhost:9090
3. Query logs: http://localhost:3100
4. Trace requests: http://localhost:16686
5. Review dashboards: http://localhost:3000

---

**Next**: Module 15d - Testing & Documentation for Module 15
