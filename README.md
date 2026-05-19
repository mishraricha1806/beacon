# Beacon
Production-readiness intelligence for modern infrastructure.
Beacon detects risky infrastructure configurations, operational anti-patterns, and production-readiness issues before deployment.
---
## Why Beacon?
Infrastructure failures are often caused by:
- weak Terraform configurations
- Kafka scaling mistakes
- insecure IAM permissions
- missing resiliency patterns
- poor operational defaults
Beacon helps platform engineers catch these risks early.
---
## Features
- Infrastructure risk analysis
- Production-readiness scoring
- Kafka operational checks
- Terraform configuration review
- AI-powered operational explanations
- CLI-first workflow
---
## Example
bash beacon scan ./examples/bad-infra
Output:
text Production Readiness Score: 61/100  CRITICAL: - Kafka topic payments has replication_factor=1 - IAM policy contains wildcard permissions - No DLQ configured for payment-consumer  Impact: Single broker failure may interrupt payment processing workflows.
---
## Philosophy
Beacon is designed to behave like a senior platform architect reviewing infrastructure for production readiness.
---
## Current Support
- Terraform
- Kafka configurations
More infrastructure platforms coming soon.
---
## Installation
``` bash pip install beaconops ```
---
## Run Locally
``` bash git clone https://github.com/<your-org>/beacon.git  cd beacon  pip install -r requirements.txt  python -m beacon.cli scan ./examples/bad-infra
---
## Roadmap
- GitHub PR reviews
- Infrastructure graph analysis
- Runtime diagnostics
- Kubernetes support
- Deployment risk intelligence
---
## License
MIT
