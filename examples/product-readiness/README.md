# Product Readiness Demo

This demo shows Beacon's first product promise:

```text
Run Beacon before production.
Understand whether the system is ready, what can break, and what to fix first.
```

## Scenarios

| Scenario | Expected Story |
| --- | --- |
| `good-infra` | Production-ready Kafka config with safe replication, retention, ownership, producer, and consumer settings. |
| `bad-infra` | Production blocker: RF=1, missing ISR, unbounded retention, large messages, unsafe producer, and weak consumer recovery. |
| `dev-exception` | A dev retry topic intentionally uses one partition; Beacon treats this as contextual when run with `--environment dev`. |
| `prod-same-risk` | The same shape becomes production-significant when run with `--environment prod`. |

## Commands

```bash
python3 -m beacon.cli readiness static examples/product-readiness/good-infra --environment prod --no-html --no-open-report
python3 -m beacon.cli readiness static examples/product-readiness/bad-infra --environment prod --no-html --no-open-report
python3 -m beacon.cli readiness static examples/product-readiness/dev-exception --environment dev --no-html --no-open-report
python3 -m beacon.cli readiness static examples/product-readiness/prod-same-risk --environment prod --no-html --no-open-report
```

Or run all:

```bash
scripts/demo_product_readiness.sh
```
