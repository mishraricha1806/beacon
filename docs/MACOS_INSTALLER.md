# Beacon macOS Installer

Beacon can be distributed as a proper macOS `.pkg` installer instead of asking
users to download and execute a raw `beacon-macos` binary.

The installer places the CLI at:

```text
/usr/local/bin/beacon
```

## Build

Run on macOS:

```bash
python3 scripts/build_macos_pkg.py
```

Or through the packaging wrapper:

```bash
./scripts/package.sh macos-pkg
```

The default output is:

```text
dist-binaries/beacon-<version>-macos.pkg
dist-binaries/beacon-<version>-macos.pkg.sha256
```

If `dist-binaries/beacon-macos` does not exist, the package builder runs the
existing PyInstaller binary build first.

To package an existing binary:

```bash
python3 scripts/build_macos_pkg.py --binary-path dist-binaries/beacon-macos
```

To fail instead of rebuilding when the binary is missing:

```bash
python3 scripts/build_macos_pkg.py --skip-binary-build
```

## Install

Users install with:

```bash
sudo installer -pkg beacon-<version>-macos.pkg -target /
```

Then run:

```bash
beacon --help
beacon readiness static ./examples/bad-infra --no-open-report
```

## Verify

```bash
shasum -a 256 -c beacon-<version>-macos.pkg.sha256
pkgutil --pkg-info ai.beacon.cli
which beacon
beacon --help
```

## Uninstall

The package installs only the Beacon CLI binary. To remove it:

```bash
sudo rm -f /usr/local/bin/beacon
sudo pkgutil --forget ai.beacon.cli
```

## Notes

- The package is currently unsigned.
- For external distribution outside your team, sign and notarize the package
  with an Apple Developer ID Installer certificate.
- The installer is read-only from Beacon's product perspective: installing the
  CLI does not grant Beacon any special infrastructure access.
