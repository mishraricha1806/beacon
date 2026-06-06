# Release Quick Reference

## Local Checks

```bash
python3 scripts/release_check_all.py --require-helm
./scripts/package.sh all
```

## Create A Release

```bash
git status
git tag -a v0.1.2 -m "Release v0.1.2"
git push origin v0.1.2
```

The tag triggers `.github/workflows/release.yml`.

## Published Artifacts

```text
beacon-<version>-macos.pkg
beacon-<version>-macos.pkg.sha256
beacon-macos
beacon-linux
beacon-windows.exe
```

Source archives, source distributions, and wheels are not part of the
recommended private-source release.

## Install

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

## Build Commands

| Command | Purpose |
| --- | --- |
| `./scripts/package.sh all` | Build private release artifacts |
| `./scripts/package.sh binary` | Build standalone binary |
| `./scripts/package.sh macos-pkg` | Build macOS installer |
| `./scripts/package.sh clean` | Clean build artifacts |
| `python3 scripts/build_macos_pkg.py` | Build `.pkg` directly |

## Before Pushing A Tag

- Full release gate passes.
- Version in `pyproject.toml` is correct.
- `git status` is clean.
- The release notes mention installer/binary artifacts only.

## Key Files

```text
.github/workflows/release.yml
scripts/build_binaries.py
scripts/build_macos_pkg.py
scripts/package.sh
docs/PACKAGING_RELEASE.md
docs/MACOS_INSTALLER.md
```
