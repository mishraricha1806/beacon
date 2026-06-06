# GitHub Setup for Private Source + Public Releases

Complete setup guide to enable the automated release workflow.

## Step 1: Repository Settings (Private)

### Make Repository Private

1. Go to **Settings** → **General**
2. Scroll to **Danger Zone**
3. Click **Change repository visibility**
4. Select **Private** → **I understand, change repository visibility**

### Protect Main Branch

1. Go to **Settings** → **Branches**
2. Add branch protection rule for `main`:
   - ✅ Require pull request reviews before merging
   - ✅ Require status checks to pass
   - ✅ Require up-to-date branches
   - ✅ Require conversation resolution

---

## Step 2: GitHub Secrets Setup

These secrets allow the release workflow to publish to PyPI.

### Create PyPI API Token

1. Go to https://pypi.org/account/register/ (if needed)
2. Go to https://pypi.org/manage/account/
3. Click **Add API token**
4. Token scope: **Entire account** (for flexibility)
5. Copy the token (starts with `pypi-`)

### Add GitHub Secret

1. Go to your repo: **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `PYPI_API_TOKEN`
4. Value: Paste your PyPI token
5. Click **Add secret**

---

## Step 3: Verify Workflow Files

The following files should exist:

```bash
ls -la .github/workflows/
```

Should show:
- ✅ `module1-release.yml` (existing - for tests on every push)
- ✅ `release.yml` (new - for creating releases on tags)

---

## Step 4: GitHub Configuration

### Enable GitHub Pages (Optional - for docs)

1. **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main`
4. Folder: `/docs`

### Configure Releases

1. **Releases** → **Create a new release** (we'll automate this later)

---

## Step 5: Local Testing Before First Release

### Test the Package Locally

```bash
# Test build locally
./scripts/package.sh check
./scripts/package.sh wheel
./scripts/package.sh test-wheel
```

### Test Binary Build

```bash
./scripts/package.sh binary
```

### Test macOS Installer Build

Run on macOS:

```bash
./scripts/package.sh macos-pkg
```

---

## Step 6: Create First Release

### Bump Version

```bash
# 1. Update VERSION file
echo "0.1.0" > VERSION

# 2. Update pyproject.toml (sync version)
# OR use a script to sync automatically

# 3. Commit
git add VERSION pyproject.toml
git commit -m "Release: bump version to 0.1.0"
git push origin main
```

### Create Release Tag

```bash
# 1. Create and push tag
git tag -a v0.1.0 -m "Release v0.1.0: Initial public release

Features:
- Static infrastructure readiness analysis
- Kafka runtime diagnostics
- Kubernetes manifest analysis
- HTML/JSON reporting"

git push origin v0.1.0
```

### Monitor Release Workflow

1. Go to **Actions** tab
2. Find **Release & Package Distribution**
3. Watch the workflow execute:
   - ✅ **test** job (3-5 min) - Runs full test suite
   - ✅ **build-pypi** job (1 min) - Builds wheel + tarball
   - ✅ **build-binaries** (5-10 min) - Builds for macOS, Linux, Windows
   - ✅ **publish-pypi** (1 min) - Publishes to PyPI
   - ✅ **create-release** (1 min) - Creates GitHub Release

### Verify Release Success

**PyPI:**
```bash
# Should find the package
pip search beacon-readiness 2>/dev/null || \
  pip index versions beacon-readiness | head -5
```

**GitHub Releases:**
1. Go to **Releases** page
2. Should see `v0.1.0` with macOS installer, binaries, and Python artifacts:
   - `beacon-0.1.0-macos.pkg`
   - `beacon-0.1.0-macos.pkg.sha256`
   - `beacon-macos`
   - `beacon-linux`
   - `beacon-windows.exe`
   - `beacon_readiness-0.1.0-py3-none-any.whl`
   - `beacon-readiness-0.1.0.tar.gz`

---

## Step 7: Continuous Releases

### Release Cycle

```bash
# 1. Make changes, commit, push
git add .
git commit -m "Feature: add new capability"
git push origin feature-branch

# 2. Create PR, get reviews, merge to main

# 3. Bump version
echo "0.2.0" > VERSION
git add VERSION
git commit -m "Release: bump to 0.2.0"
git push origin main

# 4. Create release tag (triggers workflow)
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0

# 5. Done! Workflow handles the rest
```

### Quick Release Checklist

Before pushing a tag:
- [ ] All tests pass locally: `python scripts/release_check_all.py --require-helm`
- [ ] Version bumped in VERSION file
- [ ] Git log is clean: `git log --oneline -10`
- [ ] No uncommitted changes: `git status`

---

## Step 8: User Distribution

### For pip Users

```bash
pip install beacon-readiness
beacon --help
```

### For macOS Installer Users

```bash
wget https://github.com/your-org/beacon/releases/download/v0.1.0/beacon-0.1.0-macos.pkg
sudo installer -pkg beacon-0.1.0-macos.pkg -target /
beacon --help
```

### For Binary Users

```bash
# Download from GitHub Releases
wget https://github.com/your-org/beacon/releases/download/v0.1.0/beacon-macos
chmod +x beacon-macos

# Verify (optional)
wget https://github.com/your-org/beacon/releases/download/v0.1.0/CHECKSUMS.txt
sha256sum -c CHECKSUMS.txt

# Run
./beacon-macos scan ./infrastructure
```

---

## Troubleshooting

### Workflow Fails During Tests

**Check:**
1. Go to **Actions** → failed workflow
2. Click job → see detailed error
3. Common issues:
   - Missing Helm: Already installed by `setup-helm@v4`
   - Python version: Using 3.11 by default
   - Dependencies: Check `requirements.txt`

**Fix:**
```bash
# Test locally first
python scripts/release_check_all.py --require-helm

# Or just tests
pytest tests/
```

### PyPI Upload Fails

**Check secrets:**
```bash
# Go to Settings → Secrets → Actions
# Verify PYPI_API_TOKEN is set
```

**Regenerate token if old:**
1. Go to https://pypi.org/manage/account/
2. Delete old token
3. Create new token
4. Update GitHub secret

### Binaries Not Building

**Common issues:**
- PyInstaller not installed: Added to workflow
- Hidden imports missing: Edit `scripts/build_binaries.py`
- Platform-specific: Each platform builds on itself (macOS on macOS, etc.)

---

## Advanced: Custom Release Notes

Edit `.github/workflows/release.yml` to customize release notes:

```yaml
- name: Create release notes
  run: |
    cat > release-notes.md << 'EOF'
    # Beacon v${{ github.ref_name }}
    
    ## What's New
    - Feature A
    - Fix B
    
    ## Installation
    ...
    EOF
```

---

## Advanced: Signing Releases

For production, sign releases with GPG:

```yaml
- name: Publish to PyPI (signed)
  uses: pypa/gh-action-pypi-publish@release/v1
  with:
    verbose: true
    # GPG signing requires additional setup
```

---

## Summary

| Task | File | Command |
|------|------|---------|
| **Local test** | `scripts/package.sh` | `./scripts/package.sh all` |
| **Build binary** | `scripts/build_binaries.py` | `python scripts/build_binaries.py macos` |
| **Release** | `.github/workflows/release.yml` | `git tag v0.X.Y && git push origin v0.X.Y` |
| **Users (pip)** | PyPI | `pip install beacon-readiness` |
| **Users (binary)** | GitHub Releases | Download from releases page |

Your private source + public distribution pipeline is now ready! 🚀
