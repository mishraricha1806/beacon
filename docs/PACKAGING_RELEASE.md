# Package & Release Distribution Guide

This document covers how to package and distribute Beacon as a private source repository with public binary releases.

## Overview

**Distribution Model:**
- ✅ **Source Code**: Private (on GitHub private repo)
- ✅ **PyPI Package**: Public on PyPI as `beacon-readiness`
- ✅ **Standalone Binaries**: Public GitHub Releases (macOS, Linux, Windows)
- ✅ **Users**: Install via `pip` or download pre-built binaries

---

## Part 1: Python Package (PyPI)

### Setup

The `pyproject.toml` defines the package configuration:

```toml
[project]
name = "beacon-readiness"
version = "0.1.0"
```

### Local Testing

Test the package locally before publishing:

```bash
# Install build tools
pip install build twine

# Build the distribution
python -m build

# Check for issues
twine check dist/*

# Install locally (test)
pip install dist/beacon_readiness-0.1.0-py3-none-any.whl
```

### PyPI Configuration

1. **Create PyPI Account**: https://pypi.org/account/register/
2. **Enable 2FA** (recommended)
3. **Create API Token**: https://pypi.org/manage/account/tokens/
4. **Store in GitHub Secrets**:
   - Go to repo Settings → Secrets and variables → Actions
   - Create secret: `PYPI_API_TOKEN` with your token

### Manual Publishing

```bash
# Build
python -m build

# Publish (will prompt for credentials)
twine upload dist/*

# Or use API token
twine upload -u __token__ -p $PYPI_API_TOKEN dist/*
```

### Users Install from PyPI

```bash
pip install beacon-readiness

# Run
beacon scan ./infrastructure
beacon diagnose kafka --bootstrap-server localhost:9092
beacon --help
```

---

## Part 2: Standalone Binaries

### Build Process

PyInstaller packages Python + dependencies into a single executable.

```bash
# Install build dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build binary for current platform
python scripts/build_binaries.py

# Output: dist-binaries/beacon-macos (or beacon-linux, beacon-windows.exe)
```

### Cross-Platform Builds

Build all binaries (requires GitHub Actions CI):

```bash
# macOS binary
python scripts/build_binaries.py macos

# Linux binary
python scripts/build_binaries.py linux

# Windows binary
python scripts/build_binaries.py windows
```

### Binary Artifacts

Each platform generates:
- `beacon-macos` (~100-200 MB)
- `beacon-linux` (~100-200 MB)
- `beacon-windows.exe` (~100-200 MB)
- `CHECKSUMS.txt` (SHA256 hashes for verification)

### Users Download Binaries

From GitHub Releases page:

```bash
# macOS
wget https://github.com/your-org/beacon/releases/download/v0.1.0/beacon-macos
chmod +x beacon-macos
./beacon-macos scan ./infrastructure

# Linux
wget https://github.com/your-org/beacon/releases/download/v0.1.0/beacon-linux
chmod +x beacon-linux
./beacon-linux diagnose kafka --bootstrap-server localhost:9092

# Windows
# Download beacon-windows.exe from GitHub Releases
beacon-windows.exe --help
```

### macOS `.pkg` Installer

For macOS users, prefer distributing a signed/notarized installer package over a
raw executable.

```bash
# Build the PyInstaller binary and wrap it in a macOS installer.
python3 scripts/build_macos_pkg.py

# Output:
# dist-binaries/beacon-<version>-macos.pkg
# dist-binaries/beacon-<version>-macos.pkg.sha256
```

Users install with:

```bash
sudo installer -pkg beacon-<version>-macos.pkg -target /
beacon --help
```

The installer places Beacon at `/usr/local/bin/beacon`. See
[`docs/MACOS_INSTALLER.md`](MACOS_INSTALLER.md) for build, verify, and uninstall
instructions.

---

## Part 3: Release Workflow

### Version Bumping

1. **Edit VERSION file**:
   ```bash
   echo "0.2.0" > VERSION
   ```

2. **Update pyproject.toml** (optional - can sync from VERSION):
   ```toml
   version = "0.2.0"
   ```

3. **Commit and tag**:
   ```bash
   git add VERSION pyproject.toml
   git commit -m "Bump version to 0.2.0"
   git tag -a v0.2.0 -m "Release v0.2.0"
   git push origin main
   git push origin v0.2.0
   ```

### Automated Release

When you push a tag `v*.*.*`:

1. ✅ **Tests run** on Ubuntu (Python 3.11)
2. ✅ **PyPI package builds** on Ubuntu
3. ✅ **Binaries build** on Ubuntu, macOS, Windows
4. ✅ **Package publishes** to PyPI automatically
5. ✅ **GitHub Release created** with all binaries

### Release Files Generated

```
GitHub Release (v0.2.0)
├── beacon-macos                 (macOS binary)
├── beacon-linux                 (Linux binary)
├── beacon-windows.exe           (Windows binary)
├── beacon_readiness-0.2.0-py3-none-any.whl    (Python wheel)
├── beacon-readiness-0.2.0.tar.gz              (Python tarball)
└── CHECKSUMS.txt                (SHA256 hashes)
```

---

## Part 4: Security & Best Practices

### Protecting Private Source

1. **Private Repository**
   - GitHub repo is private
   - Only team members have access to source
   - Release CI/CD is automated

2. **PyPI Does NOT Include Source**
   - PyPI package is compiled (wheels)
   - Contains only `.pyc` bytecode + dependencies
   - Source code is NOT accessible from PyPI

3. **.gitignore Protections**
   ```
   build/              # Build artifacts
   dist/               # Distribution packages
   *.egg-info/         # Egg metadata
   __pycache__/        # Compiled Python
   dist-binaries/      # Binary builds
   ```

### Verification & Trust

Users can verify downloads:

```bash
# Download binary and checksum
wget https://github.com/your-org/beacon/releases/download/v0.1.0/beacon-macos
wget https://github.com/your-org/beacon/releases/download/v0.1.0/CHECKSUMS.txt

# Verify
sha256sum -c CHECKSUMS.txt

# Output should show:
# beacon-macos: OK
```

### Python Package Safety

```bash
# Users can verify PyPI package
pip install --dry-run beacon-readiness

# Check dependencies
pip index versions beacon-readiness
```

---

## Part 5: Maintenance Checklist

### Before Each Release

- [ ] All tests pass: `python scripts/release_check_all.py --require-helm`
- [ ] Coverage is adequate: `pytest --cov=beacon tests/`
- [ ] Version bumped: `echo "X.Y.Z" > VERSION`
- [ ] README updated if needed
- [ ] CHANGELOG or release notes prepared

### Release Day

```bash
# 1. Create release tag
git tag -a vX.Y.Z -m "Release X.Y.Z - <description>"

# 2. Push to trigger CI/CD
git push origin main
git push origin vX.Y.Z

# 3. Monitor GitHub Actions
# Navigate to Actions tab → "Release & Package Distribution"

# 4. Verify PyPI upload
# https://pypi.org/project/beacon-readiness/

# 5. Verify GitHub Release
# https://github.com/your-org/beacon/releases/tag/vX.Y.Z
```

### After Release

- [ ] Announce in team channels
- [ ] Update public documentation if applicable
- [ ] Monitor for issues/feedback from users
- [ ] Plan next release based on usage

---

## Part 6: Troubleshooting

### PyPI Upload Fails

```bash
# Check credentials
twine --version

# Check package validity
python -m twine check dist/*

# Verbose upload
twine upload --verbose dist/*
```

### Binary Build Fails

```bash
# Check PyInstaller installation
pyinstaller --version

# Rebuild with verbose output
python scripts/build_binaries.py macos 2>&1 | tail -50

# Check hidden imports if modules not found
# Edit scripts/build_binaries.py to add: --hidden-import=module_name
```

### GitHub Actions Fails

- Check "Actions" tab in GitHub for detailed logs
- Ensure secrets are set: Settings → Secrets and variables → Actions
- Verify `pyproject.toml` syntax: `python -m py_compile pyproject.toml`

---

## Part 7: Distribution Examples

### For End Users

**Option A: pip (Simplest)**
```bash
pip install beacon-readiness
beacon scan ./infra
```

**Option B: Standalone Binary (No Python Install)**
```bash
# Download once, use anywhere
wget https://github.com/your-org/beacon/releases/download/v0.1.0/beacon-macos
chmod +x beacon-macos
./beacon-macos diagnose kafka --bootstrap-server localhost:9092
```

**Option C: Docker Container** (optional future)
```bash
docker run --rm -v $(pwd):/work ghcr.io/your-org/beacon:latest scan /work/infra
```

---

## Part 8: Scale to Multiple Products

Once `beacon-readiness` is working, apply the same pattern:

```bash
# beacon-docs-generator
pip install beacon-docs-generator

# beacon-integration-hub
pip install beacon-integration-hub

# beacon-policy-engine
pip install beacon-policy-engine
```

Each maintains:
- Private source repo
- Public PyPI package
- Public GitHub Releases (binaries)
- Automated CI/CD via GitHub Actions

---

## Summary

| Aspect | Method |
|--------|--------|
| **Source** | Private GitHub repo |
| **Package** | PyPI: `pip install beacon-readiness` |
| **Binaries** | GitHub Releases: `beacon-macos`, `beacon-linux`, `beacon-windows.exe` |
| **CI/CD** | GitHub Actions: Auto-build & publish on tag push |
| **Security** | Source private, package compiled, binaries verified |
| **User Access** | Full CLI tool, no source code exposure |

This model is ideal for **product-style distribution** where you maintain full source privacy while providing easy user access to stable, verified releases.
