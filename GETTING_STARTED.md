# 🚀 Getting Started: Private Repo + Packaged Releases

Your complete guide to shipping Beacon with a private source + public distribution model.

---

## ✅ Quick Checklist (30 Minutes)

### Phase 1: Local Testing (10 min)
```bash
cd /Users/richamishra/IdeaProjects/beacon

# Test local build
./scripts/package.sh check        # Verify build tools exist
./scripts/package.sh wheel        # Build Python wheel (takes 2-3 min)
./scripts/package.sh test-wheel   # Test installation (takes 2-3 min)
```

**Expected result**: 
- ✅ Build tools verified
- ✅ `dist/beacon_readiness-0.1.0-py3-none-any.whl` created (158 KB)
- ✅ Test installation successful

### Phase 2: GitHub Setup (15 min)
1. **Create PyPI Account** (5 min)
   - Go to https://pypi.org/account/register/
   - Create account (use your email)
   - Enable 2FA (optional but recommended)

2. **Generate PyPI Token** (2 min)
   - Go to https://pypi.org/manage/account/tokens/
   - Click **Add API token**
   - Name: `Beacon CI`
   - Scope: **Entire account**
   - Copy token (starts with `pypi-`)

3. **Add GitHub Secret** (3 min)
   - Go to repo **Settings** → **Secrets and variables** → **Actions**
   - Click **New repository secret**
   - Name: `PYPI_API_TOKEN`
   - Value: Paste your token
   - Click **Add secret**

4. **Make Repository Private** (5 min)
   - Go to **Settings** → **General**
   - Scroll to **Danger Zone**
   - Click **Change repository visibility**
   - Select **Private**
   - Confirm

### Phase 3: Create First Release (5 min)
```bash
# Bump version
echo "0.1.0" > VERSION

# Commit
git add VERSION
git commit -m "Release v0.1.0: Initial stable release"
git push origin main

# Create and push tag (this triggers automated release)
git tag -a v0.1.0 -m "Release v0.1.0

Features:
- Static infrastructure readiness analysis  
- Kafka runtime diagnostics
- Kubernetes manifest validation
- HTML/JSON reporting"

git push origin v0.1.0
```

### Phase 4: Monitor Release (5-15 min)
1. Go to **Actions** tab in GitHub
2. Watch **Release & Package Distribution** workflow
3. Check each job completes:
   - ✅ `test` - Tests pass (3-5 min)
   - ✅ `build-pypi` - Wheel built (1 min)
   - ✅ `build-binaries` - All platforms built (5-10 min parallel)
   - ✅ `publish-pypi` - Published to PyPI (1 min)
   - ✅ `create-release` - GitHub Release created (1 min)

### Phase 5: Verify Release (2 min)
- ✅ **PyPI**: https://pypi.org/project/beacon-readiness/
- ✅ **GitHub Releases**: https://github.com/your-org/beacon/releases
- ✅ **Test install**: `pip install beacon-readiness==0.1.0`

---

## 📋 What Each File Does

```
For Developers (You):
├── scripts/package.sh              ← Local packaging helper
├── scripts/build_binaries.py       ← Build binaries locally
├── docs/PACKAGING_RELEASE.md       ← Complete reference guide
├── docs/GITHUB_SETUP.md            ← Setup instructions
└── docs/RELEASE_QUICK_REFERENCE.md ← Quick lookup

For GitHub (Automation):
└── .github/workflows/release.yml   ← Auto-release on tag push

For Users:
├── pyproject.toml                  ← Package configuration
├── MANIFEST.in                     ← Package contents
└── Dockerfile                      ← Container option

Existing Files:
├── README.md                       ← User documentation
├── VERSION                         ← Version info
├── requirements.txt                ← Dependencies
└── beacon/                         ← Source code
```

---

## 🎯 Common Tasks

### Task: Release Version 0.2.0
```bash
echo "0.2.0" > VERSION
git add VERSION
git commit -m "Release v0.2.0"
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin main && git push origin v0.2.0
# Done! Workflow handles the rest.
```

### Task: Test Locally Before Release
```bash
./scripts/package.sh all      # Build wheel + source
./scripts/package.sh binary   # Build binaries
# Check dist/ and dist-binaries/ directories
```

### Task: Build Just macOS Binary
```bash
python3 -m venv /tmp/test-build
source /tmp/test-build/bin/activate
pip install -r requirements.txt pyinstaller
python scripts/build_binaries.py macos
# Output: dist-binaries/beacon-macos
```

### Task: Install Package Locally
```bash
# Option A: From built wheel
pip install dist/beacon_readiness-0.1.0-py3-none-any.whl

# Option B: From source
pip install -e .

# Option C: From PyPI (after release)
pip install beacon-readiness
```

### Task: Debug Workflow Failure
1. Go to **Actions** tab
2. Click failed workflow
3. Click failed job
4. Scroll to see error details
5. Common fixes:
   - Missing Helm: Already installed in workflow
   - Python version: Using 3.11
   - Missing module: Add to `scripts/build_binaries.py`

---

## 🔍 Verification

After each release, verify:

```bash
# 1. Check PyPI package exists
pip search beacon-readiness 2>/dev/null || \
  curl -s https://pypi.org/pypi/beacon-readiness/json | grep version

# 2. Check GitHub Release exists
curl -s https://api.github.com/repos/your-org/beacon/releases/latest | grep tag_name

# 3. Test installation
pip install --upgrade beacon-readiness
beacon --version

# 4. Verify binary checksums
cd dist-binaries
sha256sum -c CHECKSUMS.txt
```

---

## 📚 Documentation Quick Links

| Need | Read |
|------|------|
| **Complete details** | `docs/PACKAGING_RELEASE.md` |
| **How to setup GitHub** | `docs/GITHUB_SETUP.md` |
| **Quick commands** | `docs/RELEASE_QUICK_REFERENCE.md` |
| **What was implemented** | `IMPLEMENTATION_SUMMARY.md` |
| **What files were created** | `FILES_CREATED.md` |
| **User installation** | `README.md` |

---

## 🎓 What You've Learned

By completing this setup, you now understand:

1. **Python Packaging**: `pyproject.toml`, wheels, PyPI
2. **Binary Distribution**: PyInstaller, cross-platform builds
3. **CI/CD Automation**: GitHub Actions, triggered releases
4. **Version Control**: Git tags, semantic versioning
5. **Secret Management**: GitHub Secrets, API tokens
6. **Product Distribution**: Private source + public releases

---

## 🚨 Important Reminders

### DO ✅
- ✅ Keep repository PRIVATE
- ✅ Store PyPI token in GitHub Secrets (never commit!)
- ✅ Always run tests before releasing
- ✅ Use semantic versioning (v0.1.0, v0.2.0, v1.0.0)
- ✅ Tag before pushing (git tag, then git push)

### DON'T ❌
- ❌ Commit secrets to git
- ❌ Release without running tests
- ❌ Share PyPI token in messages/emails
- ❌ Make repository public without intention
- ❌ Push PyPI package with "unknown" version

---

## 📞 Troubleshooting

### "PyPI upload failed"
**Check**: GitHub Secrets → PYPI_API_TOKEN exists and not empty  
**Fix**: Regenerate token at https://pypi.org/manage/account/

### "Binary won't build"
**Check**: Look at Actions workflow logs  
**Common fix**: Missing hidden imports (edit `scripts/build_binaries.py`)

### "Tests fail in CI"
**Check**: Run locally first: `python scripts/release_check_all.py --require-helm`  
**Common issues**: Helm version, Python 3.11 required, dependencies missing

### "Can't find released package"
**Check**: 
- Wait 2-3 minutes (PyPI caching)
- Verify package name: `beacon-readiness` (with hyphen)
- Check https://pypi.org/project/beacon-readiness/

---

## 🏁 Success Criteria

You'll know it's working when:

1. ✅ Local wheel builds: `./scripts/package.sh wheel`
2. ✅ Test wheel installs: `./scripts/package.sh test-wheel`
3. ✅ GitHub Actions passes on `main` branch
4. ✅ Tag `v0.1.0` triggers release workflow
5. ✅ Package appears on PyPI
6. ✅ `pip install beacon-readiness` works
7. ✅ Binaries available on GitHub Releases
8. ✅ Users can use any installation method

---

## 🎉 You're Ready!

Your private source repository with public packaged releases is now ready to go! 

### Next Steps:
1. **Follow the Quick Checklist** above (30 minutes)
2. **Create your first release** with `git tag v0.1.0`
3. **Announce to users**
4. **Celebrate** 🚀

### For Future Releases:
```bash
# Change version in VERSION file
echo "0.2.0" > VERSION

# Commit, tag, and push
git add VERSION && git commit -m "Release v0.2.0" && \
  git tag -a v0.2.0 -m "Release v0.2.0" && \
  git push origin main && git push origin v0.2.0

# Everything else is automated! ✨
```

---

**Ready to release?** Start with the Quick Checklist above!

**Questions?** See the documentation files.

**Having issues?** Check the Troubleshooting section.

---

**Version**: 1.0  
**Date**: June 6, 2026  
**Status**: ✅ Ready for production

