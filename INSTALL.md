# Installation

Beacon is distributed as installer and binary artifacts so users can run it
without source-code access.

## macOS

Download `beacon-<version>-macos.pkg` from the GitHub Release, then run:

```bash
sudo installer -pkg beacon-<version>-macos.pkg -target /
beacon --help
```

The installer places Beacon at:

```text
/usr/local/bin/beacon
```

Verify the package checksum if the `.sha256` file is provided:

```bash
shasum -a 256 -c beacon-<version>-macos.pkg.sha256
```

## Linux

Download `beacon-linux` from the GitHub Release:

```bash
chmod +x beacon-linux
./beacon-linux --help
```

## Windows

Download `beacon-windows.exe` from the GitHub Release:

```powershell
beacon-windows.exe --help
```

## First Run

Start the local UI:

```bash
beacon ui
```

Then open:

```text
http://127.0.0.1:8765
```

Run a static production-readiness scan:

```bash
beacon readiness static ./examples/supported --no-open-report
```

Run a read-only Kafka diagnostic:

```bash
beacon diagnose kafka --bootstrap-server kafka.dev:9092
```

## Source Install

Source installation is for maintainers only. It is not the recommended user
distribution model.

## More

- [docs/PACKAGING_RELEASE.md](docs/PACKAGING_RELEASE.md)
- [docs/MACOS_INSTALLER.md](docs/MACOS_INSTALLER.md)
- [README.md](README.md)
