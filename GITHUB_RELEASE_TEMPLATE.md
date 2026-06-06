# GitHub Release Notes Template

## Beacon v<version>

Beacon provides production-readiness intelligence for modern infrastructure.

## Distribution

This release is distributed as installer and binary artifacts only. Source code,
Python wheels, and source distributions are not included in the public release.

## Downloads

- macOS installer: `beacon-<version>-macos.pkg`
- macOS checksum: `beacon-<version>-macos.pkg.sha256`
- macOS raw binary fallback: `beacon-macos`
- Linux binary: `beacon-linux`
- Windows binary: `beacon-windows.exe`

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

## Module 1

- Static production-readiness analysis.
- Kafka configuration readiness.
- Kubernetes manifest readiness.
- Terraform, object storage, and IAM checks.
- HTML and JSON reports.
- UI smoke validation.

## Runtime Diagnostics

- Read-only Kafka diagnostics.
- Runtime snapshot evaluation.
- Schema Registry compatibility checks.
- Deterministic root-cause hypotheses.

## Safety

- Beacon does not mutate Kafka topics, offsets, ACLs, schemas, or infrastructure.
- Runtime checks are read-only.
- Credentials should be supplied locally and not committed.

## Documentation

- `INSTALL.md`
- `docs/PACKAGING_RELEASE.md`
- `docs/MACOS_INSTALLER.md`
