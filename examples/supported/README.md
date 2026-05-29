# Beacon Supported Input Examples

These examples cover the current Module 1 release surface.

Run all static examples:

```bash
python3 -m beacon.cli readiness static examples/supported --no-html --no-open-report
```

Run runtime snapshot examples:

```bash
python3 -m beacon.cli readiness snapshot examples/supported/runtime/platform-runtime.yaml --no-html --no-open-report
python3 -m beacon.cli readiness flow examples/supported/runtime/flow-runtime.yaml --no-html --no-open-report
```

Run Prometheus collector config:

```bash
python3 -m beacon.cli readiness prometheus examples/supported/prometheus/platform-prometheus.yaml --no-html --no-open-report
```

Run OpenTelemetry export:

```bash
python3 -m beacon.cli readiness opentelemetry examples/supported/opentelemetry/checkout-otel.yaml --no-html --no-open-report
```

Run direct live collectors when you have access:

```bash
python3 -m beacon.cli readiness kafka --bootstrap-server localhost:9092 --no-html --no-open-report
python3 -m beacon.cli readiness kubernetes --namespace payments --no-html --no-open-report
```

Supported example groups:

* `terraform/` - Terraform HCL, plan JSON, and state JSON
* `kafka/` - Kafka topic and broker/server config
* `kubernetes/` - Kubernetes manifests and runtime snapshots
* `helm/` - Helm chart rendering input
* `cicd/` - GitHub Actions deployment workflow risk
* `cloud/` - Cloud inventory snapshot risk
* `topology/` - Service topology and blast-radius input
* `runtime/` - API, database, storage, and flow runtime snapshots
* `prometheus/` - Prometheus query mapping into runtime snapshots
* `opentelemetry/` - OpenTelemetry span and metric export mapping into runtime snapshots
