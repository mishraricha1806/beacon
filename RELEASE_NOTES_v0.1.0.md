# Beacon v0.1.0 Release Notes

**Release Date:** June 6, 2026

---

## Overview

Beacon v0.1.0 is the **first stable release** of production-readiness intelligence for distributed systems. This release focuses on **static infrastructure analysis, Kafka diagnostics, and operational risk detection**.

Beacon detects risky infrastructure configurations, operational anti-patterns, and runtime infrastructure risks **before they impact production systems**.

---

## What's New in v0.1.0

### ✨ Core Features

#### Module 1: Infrastructure Production Readiness (Stable)
- **Static infrastructure scanning** across multiple domains
- **Kafka configuration** readiness analysis
  - Topic replication factor, retention, compaction settings
  - Broker configuration and storage optimization
  - Consumer group and producer settings
  - ACL and security configuration
- **Kubernetes manifest** validation
  - Pod security policies
  - Resource requests/limits
  - Deployment replicas and health checks
- **Terraform configuration** analysis
  - Infrastructure as Code best practices
  - State and plan JSON scanning
- **Helm-rendered Kubernetes manifest** scanning
- **CI/CD workflow** risk detection (GitHub Actions)
- **Cloud security** (AWS, GCP, Azure)
  - Object storage exposure
  - IAM permission risks
  - Cloud inventory snapshots
- **Service topology** analysis
  - Blast radius identification
  - Dependency mapping
- **Production-readiness scoring** (0–100)
- **HTML and JSON reporting**

#### Module 2: Runtime Diagnostics (Kafka-First)
- **Live Kafka cluster diagnostics** (read-only)
  - Broker metadata and health
  - Topic configuration and partition topology
  - Consumer group lag analysis
  - Hot partition detection
  - ISR (in-sync replicas) and offline partition monitoring
  - Replication lag and broker request queue saturation
- **Schema Registry diagnostics**
  - Compatibility posture
  - Subject and schema availability
- **Kafka ACL and history analysis**
  - Security posture
  - Compliance and access patterns
- **Runtime snapshot analysis**
  - API, database, storage, and Kafka signals
- **Operational recommendations**
  - Deterministic decision engine
  - Confidence scoring
  - Evidence-based reasoning

#### Module 3: Flow Intelligence
- **Cross-system bottleneck ranking**
  - Identify which layer (API, Kafka, DB, storage) is the likely constraint
- **Deployment correlation**
  - Before/after regression detection
  - Deployment-triggered degradation identification
- **Cascading latency detection**
  - Multi-hop latency tracing
- **Root-cause hypotheses**
  - Retry cascades
  - Database bottlenecks
  - Deployment regressions
  - Storage pressure
  - Kubernetes workload instability

### 🛠️ Supported Infrastructure & Platforms

**Infrastructure Providers:**
- Terraform (HCL2, plan, state JSON)
- Helm charts (rendered manifests)
- Kubernetes YAML
- Kafka (2.0+)
- GitHub Actions workflows
- AWS (EC2, RDS, S3, security groups, cloud inventory)
- GCP (Cloud Storage, inventory snapshots)
- Azure (Storage configurations)
- Cloud-agnostic topology and runtime snapshots

**Collectors & Integrations:**
- Kubernetes runtime snapshots
- Prometheus metric queries (Kafka JMX mappings)
- OpenTelemetry span and metric exports
- Deployment event timelines

**Output Formats:**
- HTML interactive reports (auto-opens in browser)
- JSON structured output (for CI/CD integration)
- Terminal ASCII output (rich formatting)

### 🔒 Security & Safety by Design

- **Read-only diagnostics**: Beacon never modifies infrastructure
- No message consumption or production
- No topic creation, deletion, or mutation
- No offset resets or ACL modifications
- No telemetry or external calls (runs fully locally)
- Metadata and status inspection only

### 🚀 Installation & Usage

#### Option 1: pip (Recommended)
```bash
pip install beacon-readiness
beacon --help
```

#### Option 2: Standalone Binary (No Python Required)
- **macOS**: Download `beacon-macos` from [GitHub Releases](#)
- **Linux**: Download `beacon-linux` from [GitHub Releases](#)
- **Windows**: Download `beacon-windows.exe` from [GitHub Releases](#)

```bash
chmod +x beacon-macos
./beacon-macos scan ./infrastructure
```

#### Option 3: Docker
```bash
docker build -t beacon:latest .
docker run --rm -v $(pwd):/work beacon:latest scan /work/infrastructure
```

#### Option 4: From Wheel
```bash
pip install beacon_readiness-0.1.0-py3-none-any.whl
```

### 📋 Example Commands

**Infrastructure Scan:**
```bash
beacon scan ./examples/bad-infra
```

**Kafka Cluster Diagnostics:**
```bash
beacon diagnose kafka --bootstrap-server localhost:9092
```

**Kubernetes Readiness:**
```bash
beacon readiness kubernetes --namespace production --output json
```

**Flow Intelligence:**
```bash
beacon diagnose flow ./checkout-flow.yaml
```

**All-Domain Readiness:**
```bash
beacon readiness all \
  --static-path ./infrastructure \
  --snapshot ./runtime.yaml \
  --schema-registry ./schema-registry.yaml \
  --output json
```

---

## Requirements

- **Python**: 3.9, 3.10, 3.11, 3.12
- **Kafka**: 2.0 or later (for live diagnostics)
- **Kubernetes**: 1.18 or later (for manifest scanning)
- **Terraform**: 0.12+ (for HCL2 and JSON scanning)

---

## Known Limitations & Future Work

### Module 4 (Future)
- **AI/RAG Explanation Layer**: Downstream explainability and remediation advice (coming soon)

### Planned Enhancements
- Live Kubernetes diagnostics
- Prometheus metrics ingestion UI
- Deeper deployment correlation analysis
- Grafana integration
- GitHub PR reviews
- Distributed operational intelligence
- AI-assisted root-cause reasoning

### Not Supported (Current)
- OpenStack, Kubernetes operators (complex custom resources)
- Database-native workload diagnostics (focus is on integration signals)
- Real-time streaming correlation (batch/snapshot analysis only)

---

## Breaking Changes

**None** — This is the first release.

---

## Bug Fixes & Improvements

**Initial Release** — All capabilities are new. No bugs fixed from previous versions.

---

## Verified Platforms

- ✅ **macOS** 11+ (Intel & Apple Silicon)
- ✅ **Linux** (Ubuntu 20.04+, RHEL 8+, Debian 11+)
- ✅ **Windows** 10+ (via binary or WSL2)
- ✅ **CI/CD**: GitHub Actions (tested), GitLab CI (compatible)

---

## Installation & Verification

### Verify Installation
```bash
# pip users
pip install beacon-readiness
beacon --help

# binary users
./beacon-macos --help

# docker users
docker run --rm beacon --help
```

### First-Time Usage
```bash
# Try on the example infrastructure (included in repo)
beacon scan ./examples/bad-infra

# View the HTML report
# Reports open automatically in your default browser
```

---

## Checksums (For Verification)

Published binaries and wheels are signed with SHA256 checksums. After download, verify:

```bash
# Example: verify macOS binary
sha256sum beacon-macos
# Compare output to CHECKSUMS.txt on GitHub Release page
```

---

## Documentation

- **README**: https://github.com/your-org/beacon
- **Installation Guide**: [INSTALL.md](https://github.com/your-org/beacon/blob/main/INSTALL.md)
- **Usage Examples**: https://github.com/your-org/beacon/blob/main/README.md#examples
- **Quick Start**: [GETTING_STARTED.md](https://github.com/your-org/beacon/blob/main/GETTING_STARTED.md)

---

## Support & Feedback

- **Report Bugs**: https://github.com/your-org/beacon/issues
- **Request Features**: https://github.com/your-org/beacon/issues
- **Discussions**: https://github.com/your-org/beacon/discussions (if enabled)

---

## Thanks & Credits

**Beacon v0.1.0** is built with:
- [Typer](https://typer.tiangolo.com/) — CLI framework
- [Rich](https://rich.readthedocs.io/) — Terminal output formatting
- [PyYAML](https://pyyaml.org/) — YAML parsing
- [Jinja2](https://jinja.palletsprojects.com/) — HTML templating
- [Confluent Kafka](https://docs.confluent.io/kafka-clients/python/current/overview.html) — Kafka client

---

## Next Steps

1. **Install Beacon**: 
   ```bash
   pip install beacon-readiness
   ```

2. **Scan Your Infrastructure**:
   ```bash
   beacon scan ./infrastructure
   ```

3. **Review the HTML Report** (auto-opens in browser)

4. **Explore More Commands**:
   ```bash
   beacon --help
   beacon scan --help
   beacon diagnose --help
   beacon readiness --help
   ```

5. **Provide Feedback**: Help shape the future of Beacon by reporting issues or requesting features on GitHub.

---

## License

**Proprietary** — See LICENSE file in the repository.

---

**Ready to get started?** Download Beacon v0.1.0 now or install via pip!

```bash
pip install beacon-readiness
```

Happy infrastructure-readiness checking! 🚀

