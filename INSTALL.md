# Beacon - Installation & Usage Guide

**Production-readiness intelligence for distributed systems**

## Quick Install

### Option 1: pip (Recommended)
```bash
pip install beacon-readiness

# Verify installation
beacon --version

# Run your first scan
beacon scan ./infrastructure
```

### Option 2: Standalone Binary (No Python Required)

**macOS:**
```bash
wget https://github.com/your-org/beacon/releases/download/latest/beacon-macos
chmod +x beacon-macos
./beacon-macos --help
```

**Linux:**
```bash
wget https://github.com/your-org/beacon/releases/download/latest/beacon-linux
chmod +x beacon-linux
./beacon-linux --help
```

**Windows:**
- Download `beacon-windows.exe` from [GitHub Releases](https://github.com/your-org/beacon/releases)
- Run: `beacon-windows.exe --help`

### Option 3: Docker
```bash
docker build -t beacon https://github.com/your-org/beacon.git
docker run --rm -v $(pwd):/work beacon scan /work/infrastructure
```

---

## Common Tasks

### Infrastructure Readiness
```bash
beacon scan ./terraform
beacon scan ./kubernetes
beacon readiness all --static-path ./infra
```

### Kafka Diagnostics
```bash
# Live cluster analysis
beacon diagnose kafka --bootstrap-server localhost:9092

# Specific topic
beacon diagnose kafka --bootstrap-server localhost:9092 --topic payments

# Specific consumer group
beacon diagnose kafka --bootstrap-server localhost:9092 --consumer-group payment-consumer
```

### Kubernetes Analysis
```bash
beacon diagnose kubernetes --namespace production
beacon readiness kubernetes --namespace payments --output json
```

### Flow Intelligence
```bash
beacon diagnose flow ./checkout-flow.yaml
```

### Generate Reports
```bash
# HTML report (auto-opens in browser)
beacon scan ./infra

# JSON output
beacon scan ./infra --output json

# No report
beacon scan ./infra --no-html --no-open-report
```

---

## What Beacon Does

Beacon detects:
- **Infrastructure risks** in Kafka, Kubernetes, Terraform, and cloud configs
- **Runtime issues** via live diagnostics (read-only)
- **Operational anti-patterns** that could cause production failures
- **Cross-system bottlenecks** across APIs, Kafka, databases, and services

---

## Documentation

- **Full Documentation**: See the README at [https://github.com/your-org/beacon](https://github.com/your-org/beacon)
- **Release Notes**: [GitHub Releases](https://github.com/your-org/beacon/releases)
- **Issues & Feature Requests**: [GitHub Issues](https://github.com/your-org/beacon/issues)

---

## Support

**Having issues?**
- Check the [FAQ](#faq) below
- Report a bug: [GitHub Issues](https://github.com/your-org/beacon/issues)
- Ask questions: Create a discussion on GitHub

---

## FAQ

**Q: Do I need Python installed to use Beacon?**  
A: No! Download the standalone binary for your platform and run it directly.

**Q: Can I use Beacon in CI/CD?**  
A: Yes! Use the exit codes and JSON output for automation.

**Q: Is Beacon read-only?**  
A: Yes! Beacon never modifies infrastructure or consumes business data.

**Q: Which versions of Kubernetes/Kafka does Beacon support?**  
A: Kafka 2.0+, Kubernetes 1.18+. See the full README for details.

**Q: Can I run Beacon offline?**  
A: Yes! Use the binary with local YAML files. No external calls needed.

---

## Version History

Latest: **0.1.0** ([Release Notes](https://github.com/your-org/beacon/releases/tag/v0.1.0))

[See All Releases →](https://github.com/your-org/beacon/releases)

---

**License**: Proprietary  
**GitHub**: [your-org/beacon](https://github.com/your-org/beacon)  
**Contact**: [your-email@company.com](mailto:your-email@company.com)

