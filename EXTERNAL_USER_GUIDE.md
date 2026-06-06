# 🚀 Beacon v0.1.0 - External User Guide

**For Users Outside Your Organization**

---

## ⚠️ IMPORTANT: Repository Access

**Note**: The Beacon repository is currently **PRIVATE**.

If you want external users to access it, you have two options:

### **Option 1: Make Repository Public** (Recommended for Open Source)

**Steps to make repo public**:
1. Go to: https://github.com/mishraricha1806/beacon/settings
2. Scroll to "Change repository visibility"
3. Click "Change visibility"
4. Select "Public"
5. Click "I understand, change repository visibility"

Once public, users can follow the steps below.

### **Option 2: Keep Private + Grant Access** (For Specific Teams)

If you want to keep it private but allow specific people:
1. Go to: https://github.com/mishraricha1806/beacon/settings/access
2. Under "Collaborators", click "Add people"
3. Enter their GitHub usernames
4. Select permission level (usually "Read" for external users)
5. Send them the invite link

---

## 📥 Installation Methods

### **IF REPOSITORY IS PUBLIC**

#### **Method 1: Install from Source (Easiest)**

**Step 1: Clone the Repository**
```bash
git clone https://github.com/mishraricha1806/beacon.git
cd beacon
```

**Step 2: Check Python Version**
```bash
python3 --version
# Output should be: Python 3.9 or higher
```

**Step 3: Create Virtual Environment** (Recommended)
```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

**Step 4: Install Dependencies**
```bash
pip install -r requirements.txt
```

**Step 5: Verify Installation**
```bash
beacon --help
# Should show all available commands
```

---

#### **Method 2: Install via pip (After PyPI Publication)**

```bash
# One-command installation
pip install beacon-readiness

# Verify
beacon --help
```

---

#### **Method 3: Docker Installation** (If Dockerfile provided)

```bash
# Build Docker image
docker build -t beacon:latest https://github.com/mishraricha1806/beacon.git

# Run in Docker
docker run -it beacon:latest

# Or mount your configs
docker run -v $(pwd)/configs:/configs beacon:latest \
  beacon scan /configs
```

---

### **IF REPOSITORY IS PRIVATE**

#### **Method 1: Using GitHub CLI with Personal Access Token**

**Step 1: Create a Personal Access Token**
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Set name: `beacon-access`
4. Select scopes:
   - ✅ `repo` (full control of private repositories)
   - ✅ `read:user`
5. Click "Generate token"
6. **Copy the token** (you won't see it again!)

**Step 2: Clone with Token**
```bash
# Replace YOUR_TOKEN with the token you created
git clone https://YOUR_TOKEN@github.com/mishraricha1806/beacon.git
cd beacon
```

Or use authentication prompt:
```bash
git clone https://github.com/mishraricha1806/beacon.git
# When prompted for password, paste your token
```

**Step 3: Continue with Installation**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
beacon --help
```

---

#### **Method 2: Using SSH Key** (For Regular Collaborators)

**Step 1: Generate SSH Key** (if you don't have one)
```bash
ssh-keygen -t ed25519 -C "your.email@example.com"
# Press Enter to accept defaults
```

**Step 2: Add SSH Key to GitHub**
1. Copy your public key:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
2. Go to: https://github.com/settings/keys
3. Click "New SSH key"
4. Paste your public key
5. Click "Add SSH key"

**Step 3: Clone with SSH**
```bash
git clone git@github.com:mishraricha1806/beacon.git
cd beacon
```

**Step 4: Continue with Installation**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
beacon --help
```

---

#### **Method 3: Direct Access from Owner**

**If owner adds you as a collaborator**:

1. **You receive an invite** to: https://github.com/mishraricha1806/beacon
2. **Accept the invitation**
3. **Clone normally**:
   ```bash
   git clone https://github.com/mishraricha1806/beacon.git
   cd beacon
   ```
4. **GitHub will prompt for authentication** (one-time)
5. **Install dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

---

## ✅ Installation Verification

After installation, verify everything works:

```bash
# Check version
beacon --version

# Run help
beacon --help

# Try a simple command
beacon scan ./examples/bad-infra
```

Expected output:
```
Beacon Production Readiness Analysis
=====================================

Production Readiness Score: XX/100
...
```

---

## 🚀 Quick Start After Installation

### **1. Scan Your Infrastructure**
```bash
beacon scan ./my-infrastructure
```

### **2. Diagnose Live Kafka Cluster**
```bash
beacon diagnose kafka --bootstrap-server kafka.prod:9092
```

### **3. Analyze Kubernetes**
```bash
beacon diagnose kubernetes --namespace production
```

### **4. Open Web UI**
```bash
beacon ui
# Opens http://127.0.0.1:8765
```

### **5. Generate Reports**
```bash
beacon readiness all \
  --static-path ./configs \
  --snapshot ./runtime.yaml \
  --no-open-report

# View report
open reports/report.html
```

---

## 🆘 Troubleshooting

### **Issue: "Repository not found" when cloning**

**If Repository is Private**:
- ✅ Make sure you have access (invited as collaborator)
- ✅ Use personal access token or SSH key
- ✅ Check token has `repo` scope

**If Repository is Public**:
- ✅ Try: `git clone https://github.com/mishraricha1806/beacon.git` directly
- ✅ Check your internet connection

**Solution**:
```bash
# Clear git cache and try again
git config --global --unset credential.helper
git clone https://YOUR_TOKEN@github.com/mishraricha1806/beacon.git
```

---

### **Issue: "Command not found: beacon"**

**Solution**:
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall
pip install -e .

# Verify
beacon --help
```

---

### **Issue: "ModuleNotFoundError" when running beacon**

**Solution**:
```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Try again
beacon --help
```

---

### **Issue: "Permission denied" on SSH clone**

**Solution**:
```bash
# Check SSH key is added to ssh-agent
ssh-add ~/.ssh/id_ed25519

# Test SSH connection
ssh -T git@github.com

# Should show: "Hi username! You've successfully authenticated."
```

---

## 📋 System Requirements

Before installation, make sure you have:

| Requirement | Version | Check Command |
|------------|---------|----------------|
| **Python** | 3.9+ | `python3 --version` |
| **pip** | Latest | `pip --version` |
| **git** | Latest | `git --version` |
| **RAM** | 512MB+ | `free -h` (Linux) or System Preferences (macOS) |
| **Disk Space** | 200MB+ | `df -h` |

---

## 📚 Documentation References

- **Getting Started**: [INSTALL.md](./INSTALL.md)
- **Complete Guide**: [RELEASE_STEPS.md](./RELEASE_STEPS.md)
- **Features**: [README.md](./README.md)
- **Examples**: [examples/](./examples/)

---

## 🎯 RECOMMENDATION FOR YOUR TEAM

To make Beacon available to external users:

### **Best Practice: Make it Public** ✅

**Reasons**:
1. ✅ External users can clone directly
2. ✅ No authentication needed
3. ✅ Better community adoption
4. ✅ Easy installation
5. ✅ Professional open-source approach

**Steps to make public**:
1. Go to: https://github.com/mishraricha1806/beacon/settings
2. Scroll to "Change repository visibility"
3. Click "Make public"
4. Users follow simple installation: `git clone https://github.com/mishraricha1806/beacon.git`

---

## 📞 Support for External Users

If users need help:

1. **Documentation**: [INSTALL.md](./INSTALL.md), [README.md](./README.md)
2. **Issues**: [GitHub Issues](https://github.com/mishraricha1806/beacon/issues)
3. **Discussions**: [GitHub Discussions](https://github.com/mishraricha1806/beacon/discussions)

---

**Happy analyzing!** 🚀
