# Module 1 Demo

This guide runs the release-ready Module 1 path from command line and the local
readiness console.

## Command-Line Demo

Run the complete deterministic demo:

```bash
scripts/demo_module1.sh
```

The script exercises:

- static readiness over supported examples
- all-domain readiness
- bad-infra regression
- runtime snapshot analysis
- flow intelligence
- Kafka ACL export analysis
- Kafka historical trend analysis
- OpenTelemetry analysis
- Schema Registry analysis
- rule metadata catalog output

## Release Gate

Run the Module 1 release check:

```bash
python3 scripts/module1_release_check.py
```

Use the Helm-enforced mode only where the Helm CLI is installed:

```bash
python3 scripts/module1_release_check.py --require-helm
```

## Web UI Demo

Start the local readiness console:

```bash
python3 -m beacon.ui
```

Open:

```text
http://127.0.0.1:8765
```

Suggested UI checks:

- Static readiness: upload `examples/bad-infra/kafka-topics.yaml`
- Runtime snapshot: upload `examples/supported/runtime/all-runtime.yaml`
- Flow intelligence: upload `examples/supported/runtime/flow-runtime.yaml`
- Kafka ACL export: upload `examples/supported/kafka/acls.yaml`
- Kafka trend analysis: upload `examples/supported/kafka/history.yaml`
- OpenTelemetry: upload `examples/supported/opentelemetry/checkout-otel.yaml`
- Schema Registry: upload `examples/supported/kafka/schema-registry.yaml`

The UI returns the same readiness contract as the CLI: score, production
decision, top reasons, next actions, root-cause hypotheses, findings, and a JSON
download.
