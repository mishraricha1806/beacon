# Installation & Getting Started

## Quick Installation

### Option 1: From PyPI (Recommended)
```bash
pip install beacon-readiness
```

### Option 2: From Source
```bash
git clone https://github.com/mishraricha1806/beacon.git
cd beacon
pip install -r requirements.txt
```

### Option 3: With Development Tools
```bash
git clone https://github.com/mishraricha1806/beacon.git
cd beacon
pip install -r requirements.txt
pip install -e ".[dev]"  # For testing and development
```

---

## System Requirements

- **Python**: 3.9, 3.10, 3.11, or 3.12
- **OS**: Linux, macOS, or Windows
- **Memory**: Minimum 512MB (1GB+ recommended)
- **Disk Space**: 200MB for installation

---

## First-Time Usage

### 1. Run the Web UI (Easiest)

```bash
beacon ui
```

Then open: **http://127.0.0.1:8765**

### 2. Scan Infrastructure

```bash
beacon scan ./my-infrastructure
```

### 3. Analyze Live Kafka Cluster

```bash
beacon diagnose kafka --bootstrap-server kafka.prod:9092
```

### 4. Analyze Kubernetes

```bash
beacon diagnose kubernetes --namespace production
```

---

## Common Commands

```bash
# Static infrastructure readiness
beacon readiness static ./infrastructure

# Live Kafka diagnostics
beacon diagnose kafka --bootstrap-server localhost:9092

# Kubernetes analysis
beacon diagnose kubernetes --namespace production

# Generate JSON output
beacon diagnose kafka --bootstrap-server localhost:9092 --output json

# Web UI
beacon ui
```

---

## Documentation

- [README.md](./README.md) - Full feature overview
- [RELEASE_STEPS.md](./RELEASE_STEPS.md) - Complete usage guide
- [examples/](./examples/) - Example configurations

---

**Happy analyzing!** 🚀