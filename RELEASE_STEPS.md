# Beacon v0.1.0 - Release Instructions

## Step 1: Push Git Tags (From Your Local Machine)

```bash
# Navigate to your local beacon repository
cd beacon

# Create a new tag for v0.1.0
git tag -a v0.1.0 -m "Release v0.1.0 - Production-readiness intelligence for distributed systems"

# Push the tag to GitHub
git push origin v0.1.0
```

## Step 2: Create GitHub Release

**Option A: Via GitHub Web UI (Easiest)**
1. Go to: https://github.com/mishraricha1806/beacon/releases
2. Click "Create a new release"
3. Choose tag: `v0.1.0`
4. Release title: `v0.1.0 - Beacon Production Readiness Intelligence`
5. Release description: (see below)
6. Click "Publish release"

**Option B: Via GitHub CLI**

```bash
# Install GitHub CLI if you haven't: https://cli.github.com/
# Then run:

gh release create v0.1.0 \
  --title "v0.1.0 - Beacon Production Readiness Intelligence" \
  --notes "First stable release of Beacon - Production-readiness intelligence for distributed systems"
```

### Suggested Release Description:

```markdown
# Beacon v0.1.0

**First stable release of Beacon - Production-readiness intelligence for distributed systems**

## What's Included

### Module 1: Distributed System Production Readiness
- ✅ Static production readiness analysis
- ✅ Kafka configuration readiness
- ✅ Kubernetes manifest readiness
- ✅ Terraform/plan/state readiness
- ✅ Multi-domain scanning (API, Kafka, Kubernetes, Database, Security, CI/CD, Topology)
- ✅ JSON and HTML readiness reports

### Module 2: Kafka-First Runtime Diagnostics
- ✅ Live Kafka diagnostics
- ✅ Consumer group lag diagnosis
- ✅ Hot partition detection
- ✅ Schema Registry diagnostics
- ✅ Deterministic root-cause hypotheses

### Module 3: Flow Intelligence
- ✅ Cross-system bottleneck ranking
- ✅ Deployment regression detection
- ✅ Cascading latency detection across API, Kafka, consumers, storage, and databases

## Installation

### From PyPI (Coming Soon)
```bash
pip install beacon-readiness
```

### From Source
```bash
git clone https://github.com/mishraricha1806/beacon.git
cd beacon
pip install -r requirements.txt
```

## Quick Start

### Infrastructure Scan
```bash
python3 -m beacon.cli scan ./examples/bad-infra
```

### Live Kafka Diagnostics
```bash
python3 -m beacon.cli diagnose kafka --bootstrap-server localhost:9092
```

### Web UI
```bash
python3 -m beacon.ui
# Open http://127.0.0.1:8765
```

## Documentation

- [README](https://github.com/mishraricha1806/beacon/blob/main/README.md) - Full feature overview
- [Module 1 Release Details](https://github.com/mishraricha1806/beacon/blob/main/docs/MODULE_1_RELEASE.md)
- [Kafka Release Details](https://github.com/mishraricha1806/beacon/blob/main/docs/KAFKA_RELEASE.md)
- [Project Demo](https://github.com/mishraricha1806/beacon/blob/main/docs/PROJECT_DEMO.md)

## Example: Black Friday Production Readiness Demo
See [examples/demo-black-friday](https://github.com/mishraricha1806/beacon/tree/main/examples/demo-black-friday) for a complete end-to-end scenario.

## Supported Domains
- **Infrastructure**: Terraform, Helm, Kubernetes YAML, Kafka configs, CI/CD, Cloud inventory
- **Runtime**: Kafka, Kubernetes, API/service, databases, storage
- **Observability**: Prometheus, OpenTelemetry, Schema Registry

## License
Proprietary - Beacon Team

## Support
For issues, questions, or feedback: [Create an Issue](https://github.com/mishraricha1806/beacon/issues)
```

---

## Using Beacon as an External User

After the release is complete, external users can install and use Beacon in these ways:

### Installation

#### Method 1: Install from PyPI (Recommended - Once Published)
```bash
pip install beacon-readiness
```

#### Method 2: Install from Source
```bash
git clone https://github.com/mishraricha1806/beacon.git
cd beacon
pip install -r requirements.txt
```

#### Method 3: Docker (Recommended for Isolated Environments)
```bash
# If a Dockerfile is provided
docker build -t beacon:latest .
docker run -it beacon:latest
```

---

### Basic Usage Examples

#### 1. **Scan Infrastructure Configurations**
```bash
# Scan a directory of configs
beacon scan ./my-infrastructure

# Output: Production readiness report with findings
```

#### 2. **Diagnose Live Kafka Cluster**
```bash
# Connect to Kafka cluster
beacon diagnose kafka --bootstrap-server kafka.prod:9092

# With specific topic
beacon diagnose kafka --bootstrap-server kafka.prod:9092 --topic payments

# With specific consumer group
beacon diagnose kafka --bootstrap-server kafka.prod:9092 --consumer-group payment-processor
```

#### 3. **Kubernetes Runtime Analysis**
```bash
# Analyze running Kubernetes cluster
beacon diagnose kubernetes --namespace production

# Get readiness assessment
beacon readiness kubernetes --namespace production --output json
```

#### 4. **Web UI Dashboard**
```bash
# Start interactive web interface
beacon ui

# Opens: http://127.0.0.1:8765
```

#### 5. **Generate Reports**
```bash
# Static readiness analysis with HTML report
beacon readiness static ./configs/terraform

# Output: reports/report.html (auto-opens in browser)

# JSON output for automation
beacon diagnose kafka --bootstrap-server localhost:9092 --output json
```

#### 6. **All-Domain Analysis**
```bash
beacon readiness all \
  --static-path ./examples/supported \
  --snapshot ./examples/supported/runtime/all-runtime.yaml \
  --deployment-events ./examples/supported/deployments/events.yaml \
  --opentelemetry ./examples/supported/opentelemetry/checkout-otel.yaml \
  --schema-registry ./examples/supported/kafka/schema-registry.yaml \
  --no-open-report
```

---

### Supported Input Formats

Users can provide:

| Type | Format | Usage |
|------|--------|-------|
| **Terraform** | HCL, JSON plan, JSON state | `beacon scan ./terraform/` |
| **Kubernetes** | YAML manifests | `beacon scan ./k8s/` |
| **Helm** | Rendered manifests | `beacon scan ./helm-rendered/` |
| **Kafka** | Config YAML, JMX metrics | `beacon diagnose kafka --bootstrap-server HOST` |
| **CI/CD** | GitHub Actions workflows | `beacon scan ./github-workflows/` |
| **Runtime Snapshots** | YAML snapshots | `beacon runtime ./snapshots/api-runtime.yaml` |
| **Prometheus** | Scrape config + metrics | `beacon diagnose prometheus config.yaml` |
| **OpenTelemetry** | Spans/metrics export | `beacon diagnose opentelemetry otel.yaml` |

---

### Example: Full Production Readiness Check

```bash
#!/bin/bash

# 1. Static infrastructure analysis
echo "📋 Analyzing infrastructure configurations..."
beacon readiness static ./infrastructure/terraform

# 2. Live Kafka diagnostics
echo "🔍 Diagnosing Kafka cluster..."
beacon diagnose kafka \
  --bootstrap-server kafka.prod:9092 \
  --topic payments

# 3. Kubernetes runtime analysis
echo "☸️  Analyzing Kubernetes cluster..."
beacon diagnose kubernetes --namespace production

# 4. Generate comprehensive report
echo "📊 Generating comprehensive report..."
beacon readiness all \
  --static-path ./infrastructure \
  --snapshot ./runtime-snapshots/current.yaml \
  --deployment-events ./deployments/events.yaml

echo "✅ Analysis complete! View report at: reports/report.html"
```

---

### Example: CI/CD Integration

```yaml
# .github/workflows/production-readiness.yml
name: Production Readiness Check

on:
  pull_request:
    paths:
      - 'infrastructure/**'
      - 'kubernetes/**'

jobs:
  readiness-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Beacon
        run: pip install beacon-readiness
      
      - name: Run production readiness scan
        run: beacon readiness static ./infrastructure --output json > readiness.json
      
      - name: Comment results on PR
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const results = JSON.parse(fs.readFileSync('readiness.json'));
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `📊 Production Readiness Score: ${results.score}/100`
            });
```

---

## Next Steps to Complete Release

1. **Execute local Git commands** (from your machine):
   ```bash
   cd beacon
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin v0.1.0
   ```

2. **Create GitHub Release** (Web UI or CLI)
   - Go to: https://github.com/mishraricha1806/beacon/releases/new
   - Select tag `v0.1.0`
   - Add release title and description
   - Click "Publish"

3. **Publish to PyPI** (Optional but Recommended)
   ```bash
   pip install build twine
   python -m build
   python -m twine upload dist/*
   ```

4. **Announce Release**
   - Post release notes in repository discussions
   - Update README with installation instructions
   - Share with your team/community

---

**That's it!** Your repository will then be available for external users to install via:
```bash
pip install beacon-readiness
```

And they can follow the usage examples above to analyze their infrastructure!
