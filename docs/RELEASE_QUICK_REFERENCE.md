# Quick Reference: Packaging & Release

## 🚀 Quick Start (5 minutes)

### 1. Test Locally
```bash
./scripts/package.sh check          # Verify build tools
./scripts/package.sh wheel          # Build Python wheel
./scripts/package.sh test-wheel     # Test installation
```

### 2. Setup GitHub Secrets
```
Settings → Secrets and variables → Actions → New repository secret
Name: PYPI_API_TOKEN
Value: [your PyPI API token from https://pypi.org/manage/account/tokens/]
```

### 3. Make Repository Private
```
Settings → General → Danger Zone → Change repository visibility → Private
```

### 4. Create Release
```bash
echo "0.1.0" > VERSION
git add VERSION
git commit -m "Release v0.1.0"
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin main
git push origin v0.1.0
```

## 📦 What Gets Created

When you push tag `v0.1.0`:

```
PyPI: beacon-readiness==0.1.0
├── pip install beacon-readiness

GitHub Release: v0.1.0
├── beacon-macos                    (170 MB)
├── beacon-linux                    (170 MB)  
├── beacon-windows.exe              (180 MB)
├── beacon_readiness-0.1.0-py3-none-any.whl
├── beacon-readiness-0.1.0.tar.gz
└── CHECKSUMS.txt                   (SHA256 hashes)
```

## 👥 Users Install

### Option A: pip (Recommended)
```bash
pip install beacon-readiness
beacon scan ./infra
```

### Option B: Standalone Binary
```bash
# Download
wget https://github.com/your-org/beacon/releases/download/v0.1.0/beacon-macos
chmod +x beacon-macos

# Verify (optional)
sha256sum -c CHECKSUMS.txt

# Run
./beacon-macos diagnose kafka --bootstrap-server localhost:9092
```

## 📋 Release Checklist

Before `git push origin v0.X.Y`:

- [ ] All tests pass: `python scripts/release_check_all.py --require-helm`
- [ ] VERSION file updated: `cat VERSION`
- [ ] pyproject.toml version matches
- [ ] No uncommitted changes: `git status`
- [ ] Git is on main branch: `git branch`

## 🔧 Build Commands

| Command | Purpose |
|---------|---------|
| `./scripts/package.sh check` | Verify build tools |
| `./scripts/package.sh wheel` | Build Python wheel only |
| `./scripts/package.sh source` | Build source tarball |
| `./scripts/package.sh binary` | Build standalone binary |
| `./scripts/package.sh test-wheel` | Test wheel installation |
| `./scripts/package.sh clean` | Clean build artifacts |

## 🐛 Troubleshooting

### "ModuleNotFoundError" when building binary
**Fix:** Edit `scripts/build_binaries.py`, add to `pyinstaller_args`:
```python
"--hidden-import=your_module",
```

### PyPI upload fails
**Fix:** Check GitHub secret:
1. Go to Settings → Secrets and variables → Actions
2. Verify `PYPI_API_TOKEN` exists and is not empty
3. Check token hasn't expired at https://pypi.org/manage/account/

### Tests fail in CI
**Fix:** Run locally first:
```bash
python scripts/release_check_all.py --require-helm
pytest tests/ -v
```

## 📚 Documentation

- **[PACKAGING_RELEASE.md](PACKAGING_RELEASE.md)** - Complete packaging guide
- **[GITHUB_SETUP.md](GITHUB_SETUP.md)** - GitHub configuration steps
- **[../README.md](../README.md)** - Project overview

## 🔐 Security

✅ **Source Private**: GitHub repo is private
✅ **Package Safe**: PyPI wheels are compiled (no source)
✅ **Binaries Verified**: SHA256 checksums included
✅ **Automated**: No manual publishing needed

## 📈 Scaling to Multiple Products

Once `beacon-readiness` works:

```bash
# beacon-docs-generator
git clone https://github.com/your-org/beacon-docs.git
cd beacon-docs
# Use same: pyproject.toml, scripts/, .github/workflows/
# Update: name = "beacon-docs-generator" in pyproject.toml

# beacon-policy-engine
git clone https://github.com/your-org/beacon-policy.git
cd beacon-policy
# Same pattern...
```

## 🎯 Key Files

```
beacon/
├── pyproject.toml                  ← Package configuration
├── VERSION                         ← Version (0.1.0)
├── MANIFEST.in                     ← Include files in package
├── .gitignore                      ← Ignore build artifacts
├── .github/workflows/
│   ├── module1-release.yml         ← Test on every push
│   └── release.yml                 ← Auto-build & publish on tag
└── scripts/
    ├── package.sh                  ← Local packaging helper
    └── build_binaries.py           ← PyInstaller wrapper
```

## 🚦 Workflow Visualization

```
You: git push origin v0.1.0
    ↓
GitHub Actions: Release & Package Distribution
    ├─→ test (3-5 min)          [Run all tests]
    ├─→ build-pypi (1 min)      [Build .whl + .tar.gz]
    ├─→ build-binaries (5-10 min) [Build macOS, Linux, Windows]
    ├─→ publish-pypi (1 min)    [Upload to PyPI]
    └─→ create-release (1 min)  [Create GitHub Release]
    ↓
Users:
    ├─→ pip install beacon-readiness
    └─→ Download from GitHub Releases
```

## ✨ Pro Tips

1. **Version your releases**: Always use `v` prefix for tags: `v0.1.0`, `v0.2.0`
2. **Atomic releases**: Push version commit + tag together
3. **Monitor workflow**: Watch Actions tab after pushing tag
4. **Verify release**: Check PyPI + GitHub Releases appear within 2 min
5. **Announce**: Post release announcement after successful upload

## 📞 Support

- **PyPI Issues**: https://pypi.org/help/
- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Beacon Issues**: Create GitHub issue in private repo

---

**Status**: ✅ Ready for production use  
**Tested**: macOS, Linux (via GitHub Actions)  
**Users**: Can install via `pip` or download binaries

