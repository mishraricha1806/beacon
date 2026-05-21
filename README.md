# Beacon

Production-readiness intelligence for modern infrastructure.

Beacon detects risky infrastructure configurations, operational anti-patterns, and production-readiness issues before deployment.

---

## Why Beacon?

Infrastructure failures are often caused by:

* weak Terraform configurations
* Kafka scaling mistakes
* insecure IAM permissions
* missing resiliency patterns
* poor operational defaults

Beacon helps platform engineers catch these risks early.

---

## Current Features

* Kafka production-readiness checks
* Terraform infrastructure validation
* Infrastructure risk scoring
* Operational risk explanations
* CLI-first workflow

---

## Example

Run Beacon against infrastructure configuration files:

```bash
python3 -m beacon.cli ./examples/bad-infra
```

Example output:

```text
Beacon Production Readiness Score: 41/100

CRITICAL:
- Kafka topic 'payments' has replication factor 1
- S3 bucket public access protection is weak

HIGH:
- Kafka topic 'payments' has low partition count
- Kafka topic 'orders' has low partition count

MEDIUM:
- Kafka topic retention below recommended production threshold

Impact:
A broker failure can make topics unavailable and interrupt production workflows.
```

---

## Current Support

Beacon currently supports:

* Terraform (`.tf`)
* Kafka YAML configurations (`.yaml`, `.yml`)

---

## Project Structure

```text
beacon/
├── beacon/
│   ├── cli.py
│   ├── scanner.py
│   ├── rules.py
│   └── reporter.py
│
├── examples/
│   └── bad-infra/
│       ├── kafka-topics.yaml
│       └── main.tf
│
├── tests/
├── README.md
└── requirements.txt
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/<your-username>/beacon.git

cd beacon
```

Install dependencies:

```bash
pip3 install -r requirements.txt
```

---

## Run Beacon

```bash
python3 -m beacon.cli ./examples/bad-infra
```

---

## Philosophy

Beacon is designed to behave like a senior platform architect reviewing infrastructure for production readiness.

The goal is not just detecting configuration issues, but explaining their operational impact before production deployment.

---

## Roadmap

* GitHub PR reviews
* AI-powered operational explanations
* Infrastructure graph analysis
* Kafka lag diagnostics
* Kubernetes support
* Runtime operational intelligence

---

## License


