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

## Sign And Notarize

Unsigned packages can trigger this macOS Gatekeeper warning:

```text
Apple could not verify "beacon-<version>-macos.pkg" is free of malware.
```

For external sharing, sign the package with an Apple Developer ID Installer
certificate and notarize it with Apple:

```bash
python3 scripts/build_macos_pkg.py \
  --skip-binary-build \
  --sign-identity "Developer ID Installer: Your Name (TEAMID)" \
  --notarize \
  --apple-id "you@example.com" \
  --apple-team-id "TEAMID" \
  --apple-password "app-specific-password"
```

GitHub Actions supports this when these secrets are configured in the private
source repository:

```text
MACOS_INSTALLER_CERTIFICATE_BASE64
MACOS_INSTALLER_CERTIFICATE_PASSWORD
MACOS_INSTALLER_SIGN_IDENTITY
MACOS_SIGNING_KEYCHAIN_PASSWORD
APPLE_ID
APPLE_TEAM_ID
APPLE_APP_SPECIFIC_PASSWORD
```

`MACOS_INSTALLER_CERTIFICATE_BASE64` should be a base64-encoded `.p12` export of
the Apple Developer ID Installer certificate.

Create it locally with:

```bash
base64 -i developer-id-installer.p12 | pbcopy
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

- Unsigned packages are suitable only for internal testing.
- External distribution should use a signed and notarized package.
- The installer is read-only from Beacon's product perspective: installing the
  CLI does not grant Beacon any special infrastructure access.
