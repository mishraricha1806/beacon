# GitHub Setup For Private Source Releases

Beacon's recommended release model is:

```text
private source repo -> public GitHub Release artifacts
```

Users receive installers and standalone binaries. They do not need repository
access.

## Repository

1. Keep the GitHub repository private.
2. Protect `main`.
3. Require release checks before merging release changes.

## Required Workflow

The release workflow lives at:

```text
.github/workflows/release.yml
```

It runs release checks, builds platform binaries, builds the macOS `.pkg`, and
uploads only binary/installer artifacts to GitHub Releases.

No PyPI token is required for the private-source release path.

## Local Release Check

Run before tagging:

```bash
python3 scripts/release_check_all.py --require-helm
```

## Local Artifact Build

```bash
./scripts/package.sh all
```

On macOS, this also creates:

```text
dist-binaries/beacon-<version>-macos.pkg
```

## Create A Release Tag

```bash
git tag -a v0.1.2 -m "Release v0.1.2"
git push origin v0.1.2
```

## Verify GitHub Release

The release should include:

```text
beacon-<version>-macos.pkg
beacon-<version>-macos.pkg.sha256
beacon-macos
beacon-linux
beacon-windows.exe
```

It should not include source distributions or wheels unless you intentionally
change the distribution model.

## User Install Paths

macOS:

```bash
sudo installer -pkg beacon-<version>-macos.pkg -target /
beacon --help
```

Linux:

```bash
chmod +x beacon-linux
./beacon-linux --help
```

Windows:

```powershell
beacon-windows.exe --help
```
