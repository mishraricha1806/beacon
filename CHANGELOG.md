CHANGELOG.md
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-06

### Added
- **Module 1: Distributed System Production Readiness** - First stable release
  - Static infrastructure readiness analysis
  - Kafka configuration and broker readiness checks
  - Kubernetes manifest readiness validation
  - Terraform HCL, plan JSON, and state JSON analysis
  - Helm-rendered manifest scanning
  - Multi-domain coverage: API, Kafka, Kubernetes, database, storage, security/IAM, CI/CD, topology
  - JSON and HTML report generation
  
- **Module 2: Kafka-First Runtime Diagnostics**
  - Live Kafka cluster diagnostics via direct broker connection
  - Consumer group lag diagnosis and trending
  - Hot partition detection and analysis
  - Schema Registry compatibility and availability checks
  - Kafka ACL and broker security assessment
  - Deterministic root-cause hypotheses for operational issues
  - Consumer rebalancing diagnostics
  - Producer throughput and durability analysis
  - Storage pressure and retention configuration analysis
  
- **Module 3: Flow Intelligence**
  - Cross-system bottleneck ranking and correlation
  - Deployment before/after regression detection
  - Cascading latency detection across API, Kafka, consumers, storage, and databases
  - Multi-service degradation pattern detection
  - Operational recommendation engine
  
- **Infrastructure Support**
  - Terraform HCL, plan JSON, and state JSON
  - Kubernetes YAML manifests and runtime snapshots
  - Kafka topic, broker, producer, consumer configurations
  - GitHub Actions workflow risk detection
  - AWS (S3, RDS, EC2, security groups) inventory analysis
  - GCP object storage analysis
  - Azure storage configuration analysis
  - Helm chart rendering support
  - Service topology and blast-radius mapping
  
- **Runtime Intelligence**
  - Runtime snapshot analysis (API, database, storage)
  - Prometheus metrics collection and analysis
  - OpenTelemetry span and metric export support
  - Schema Registry collector integration
  - Kafka JMX exporter metrics mapping
  
- **User Interfaces**
  - Command-line interface (CLI) with comprehensive subcommands
  - Web-based UI dashboard at http://127.0.0.1:8765
  - HTML report generation with visual formatting
  - JSON output for automation and integration
  
- **Safety & Design**
  - Read-only diagnostic mode (no infrastructure mutations)
  - Lightweight, low-latency analysis
  - Deterministic-first reasoning (no AI guessing)
  - Metadata-driven evaluation
  - No message consumption or production on Kafka
  - No topic/ACL modifications

### Supported Commands
- `beacon scan` - Infrastructure static analysis
- `beacon readiness` - Production readiness assessment
- `beacon diagnose` - Runtime diagnostics and issue detection
- `beacon ui` - Interactive web dashboard
- Multiple input formats and domains (static, Kafka, Kubernetes, Prometheus, OpenTelemetry, etc.)

### Documentation
- Comprehensive README with feature overview
- Module-specific release documentation
- Black Friday production readiness demo scenario
- Example configurations for all supported domains
- API and CLI usage guides

### Known Limitations (Future Work)
- Module 4 (AI/RAG Explanation Layer) - Planned for future release
- Live Kubernetes operator diagnostics - Coming in next release
- Broader OpenTelemetry support - Planned expansion
- Direct cloud provider runtime collectors - Roadmap item
- Grafana and Splunk integration - Planned for future release

[0.1.0]: https://github.com/mishraricha1806/beacon/releases/tag/v0.1.0
