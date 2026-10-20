# Private-Source Release Guide

Beacon should be released as installer and binary artifacts, not as source.

## Release Model

- Source repository: private.
- Source repository releases: internal only.
- Public artifacts: publish from an artifact-only distribution repository.
- macOS primary artifact: `.pkg` installer.
- Linux artifact: standalone `beacon-linux` binary.
- Windows artifact: standalone `beacon-windows.exe` binary.
- Integrity metadata: publish a SHA256 manifest, SPDX SBOM, and build-provenance attestations with every release.

Do not publish source distributions for private-source releases. Avoid PyPI unless
you intentionally want Python package contents exposed to users; Python wheels can
include readable project modules.

Do not share GitHub Releases from the private source repository with users. GitHub
automatically attaches `Source code (zip)` and `Source code (tar.gz)` archives to
tag-based releases. Those archives contain the repository contents.

## Build Locally

```bash
./scripts/package.sh all
```

On macOS this builds:

```text
dist-binaries/beacon-macos
dist-binaries/beacon-<version>-macos.pkg
dist-binaries/beacon-<version>-macos.pkg.sha256
```

On Linux or Windows this builds the platform binary. The macOS installer must be
built on macOS because it uses Apple's `pkgbuild` and `productbuild` tools.

## Build Individual Artifacts

```bash
python3 scripts/build_binaries.py macos
python3 scripts/build_binaries.py linux
python3 scripts/build_binaries.py windows
python3 scripts/build_macos_pkg.py
```

The package helper also exposes:

```bash
./scripts/package.sh binary
./scripts/package.sh macos-pkg
./scripts/package.sh clean
```

Wheel and source commands remain for internal development only. They are not part
of the recommended private-source release path.

## Automated Build

Push a version tag:

```bash
git tag -a v0.1.2 -m "Release v0.1.2"
git push origin v0.1.2
```

The workflow runs the release checks, builds the platform binaries, wraps the
macOS binary into a `.pkg`, generates checksums and an SPDX SBOM, creates build
and SBOM attestations, and uploads the artifacts to GitHub Actions.

The source repository workflow intentionally does not create an external GitHub
Release by default.

## Release Artifacts

Publish these files from a separate distribution repository:

```text
beacon-<version>-macos.pkg
beacon-<version>-macos.pkg.sha256
beacon-macos
beacon-linux
beacon-windows.exe
SHA256SUMS
beacon.spdx.json
```

See [PUBLIC_DISTRIBUTION.md](PUBLIC_DISTRIBUTION.md) for the artifact-only
sharing flow.

## macOS Install

```bash
sudo installer -pkg beacon-<version>-macos.pkg -target /
beacon --help
```

For Docker-first distribution, prefer the public image flow in
[PUBLIC_DISTRIBUTION.md](PUBLIC_DISTRIBUTION.md). Native macOS installer
artifacts require Apple signing/notarization before they are friendly for
external users.

## Release Gate

Before tagging:

```bash
python3 scripts/release_check_all.py --require-helm
```

The release gate validates Module 1, Module 2, Module 3, UI smoke coverage, and
packaging metadata.

## Signing

The workflow signs and notarizes the macOS installer when the documented Apple
credentials are configured. An unsigned local build is suitable only for
development; broad distribution requires a successful signing and notarization
step.

See [REPOSITORY_ADMIN_CHECKLIST.md](REPOSITORY_ADMIN_CHECKLIST.md) for the host
settings, protected checks, and release approvals that cannot be encoded in the
repository itself.
