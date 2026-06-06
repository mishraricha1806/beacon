# v0.1.0 Release Notes — Quick Summary

**Beacon v0.1.0** | June 6, 2026 | First Release

---

## 🎯 One-Line Summary
**Production-readiness intelligence for distributed systems** — scan infrastructure, diagnose Kafka/Kubernetes, and detect risks before they hit production.

---

## ✨ What You Get

### Static Analysis (Module 1)
✅ Kafka readiness (topics, brokers, consumers, security)
✅ Kubernetes manifest validation
✅ Terraform configuration scanning
✅ Cloud security analysis (AWS/GCP/Azure)
✅ CI/CD workflow risk detection
✅ Production-readiness score (0–100)

### Runtime Diagnostics (Module 2)
✅ Live Kafka cluster analysis (read-only)
✅ Consumer lag and hot partition detection
✅ Schema Registry compatibility checks

### Flow Intelligence (Module 3)
✅ Cross-system bottleneck ranking
✅ Deployment issue correlation
✅ Root-cause hypothesis generation

---

## 📥 Install (Pick One)

**pip:**
```bash
pip install beacon-readiness
```

**Binary:** Download from GitHub Releases (macOS, Linux, Windows)

**Docker:**
```bash
docker build -t beacon .
docker run --rm -v $(pwd):/work beacon scan /work/infrastructure
```

---

## 🚀 Quick Start

```bash
# Scan your infrastructure
beacon scan ./examples/bad-infra

# Check Kafka health
beacon diagnose kafka --bootstrap-server localhost:9092

# Get JSON output for CI/CD
beacon readiness all --static-path ./terraform --output json --no-html
```

---

## 🔒 Safety

- ✅ Read-only (never modifies infrastructure)
- ✅ No telemetry or external calls
- ✅ Runs 100% locally
- ✅ Safe for production use

---

## ✅ Requirements

- Python 3.9–3.12 (for pip) **OR** Just download binary (no Python needed!)
- Kafka 2.0+ (for live diagnostics)
- Kubernetes 1.18+ (for manifest scanning)
- Terraform 0.12+ (for HCL scanning)

---

## 📖 Documentation

- **[INSTALL.md](https://github.com/your-org/beacon/blob/main/INSTALL.md)** — Installation guide
- **[README.md](https://github.com/your-org/beacon/blob/main/README.md)** — Full feature list
- **[GETTING_STARTED.md](https://github.com/your-org/beacon/blob/main/GETTING_STARTED.md)** — Quick start
- **[RELEASE_NOTES_v0.1.0.md](https://github.com/your-org/beacon/blob/main/RELEASE_NOTES_v0.1.0.md)** — Detailed release notes

---

## 🐛 Known Limitations

- Module 4 (AI explanations) — coming soon
- Kubernetes live diagnostics — coming soon
- Prometheus UI — coming soon

---

## 🤝 Support

- **Issues:** https://github.com/your-org/beacon/issues
- **Features:** https://github.com/your-org/beacon/issues

---

## ✅ Installation Verified On

| OS | Status |
|----|--------|
| macOS 11+ (Intel & Apple Silicon) | ✅ Tested |
| Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+) | ✅ Tested |
| Windows 10+ (binary or WSL2) | ✅ Tested |

---

**Start using Beacon now:**

```bash
pip install beacon-readiness
beacon --help
```

🚀 Happy infrastructure readiness checking!

