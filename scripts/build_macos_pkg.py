#!/usr/bin/env python3
"""
Build a macOS .pkg installer for Beacon.

The installer places the Beacon CLI at:

    /usr/local/bin/beacon

It wraps the existing PyInstaller binary build instead of asking users to
download and chmod a raw beacon-macos executable.
"""

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IDENTIFIER = "ai.beacon.cli"
DEFAULT_OUTPUT_DIR = ROOT / "dist-binaries"


def read_version():
    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("version"):
                return line.split("=", 1)[1].strip().strip('"')

    version = ROOT / "VERSION"
    if version.exists():
        return version.read_text(encoding="utf-8").strip()

    return "0.0.0"


def require_macos():
    if platform.system() != "Darwin":
        raise RuntimeError("macOS .pkg builds must run on macOS.")


def require_tool(tool):
    resolved = shutil.which(tool)
    if not resolved:
        raise RuntimeError(f"{tool} is required to build a macOS installer.")
    return resolved


def run(command):
    print(" ".join(str(part) for part in command))
    subprocess.run(command, cwd=ROOT, check=True)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_binary(args):
    if args.binary_path:
        binary = Path(args.binary_path).expanduser().resolve()
        if not binary.exists():
            raise FileNotFoundError(f"Binary not found: {binary}")
        return binary

    binary = ROOT / "dist-binaries" / "beacon-macos"
    if binary.exists() and args.skip_binary_build:
        return binary

    if args.skip_binary_build:
        raise FileNotFoundError(
            "dist-binaries/beacon-macos was not found. Remove --skip-binary-build "
            "or pass --binary-path."
        )

    run([sys.executable, "scripts/build_binaries.py", "macos"])

    if not binary.exists():
        raise FileNotFoundError(f"Expected PyInstaller binary was not created: {binary}")

    return binary


def build_pkg(args):
    require_macos()
    require_tool("pkgbuild")
    require_tool("productbuild")

    if args.notarize:
        require_tool("xcrun")

    version = args.version or read_version()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    binary = ensure_binary(args)

    work_dir = ROOT / "build" / "macos-pkg"
    pkgroot = work_dir / "pkgroot"
    component_pkg = work_dir / f"beacon-{version}-component.pkg"
    final_pkg = output_dir / f"beacon-{version}-macos.pkg"

    if work_dir.exists():
        shutil.rmtree(work_dir)

    install_dir = pkgroot / "usr" / "local" / "bin"
    install_dir.mkdir(parents=True, exist_ok=True)
    staged_binary = install_dir / "beacon"
    shutil.copy2(binary, staged_binary)
    os.chmod(staged_binary, 0o755)

    run(
        [
            "pkgbuild",
            "--root",
            str(pkgroot),
            "--identifier",
            args.identifier,
            "--version",
            version,
            "--install-location",
            "/",
            str(component_pkg),
        ]
    )

    productbuild_command = ["productbuild", "--package", str(component_pkg)]
    if args.sign_identity:
        productbuild_command.extend(["--sign", args.sign_identity])
    productbuild_command.append(str(final_pkg))
    run(productbuild_command)

    if args.notarize:
        notarize_pkg(final_pkg, args)

    checksum = sha256_file(final_pkg)
    checksum_file = output_dir / f"{final_pkg.name}.sha256"
    checksum_file.write_text(f"{checksum}  {final_pkg.name}\n", encoding="utf-8")

    print("\nBeacon macOS installer built")
    print(f"  Package:  {final_pkg}")
    print(f"  SHA256:   {checksum}")
    print("  Installs: /usr/local/bin/beacon")
    if args.sign_identity:
        print(f"  Signed:   {args.sign_identity}")
    if args.notarize:
        print("  Notarized and stapled: yes")

    return final_pkg


def notarize_pkg(pkg_path, args):
    if not args.apple_id or not args.apple_team_id or not args.apple_password:
        raise RuntimeError("--notarize requires --apple-id, --apple-team-id, and --apple-password.")

    run(
        [
            "xcrun",
            "notarytool",
            "submit",
            str(pkg_path),
            "--apple-id",
            args.apple_id,
            "--team-id",
            args.apple_team_id,
            "--password",
            args.apple_password,
            "--wait",
        ]
    )
    run(["xcrun", "stapler", "staple", str(pkg_path)])


def parse_args():
    parser = argparse.ArgumentParser(description="Build Beacon macOS .pkg installer.")
    parser.add_argument(
        "--binary-path",
        help="Existing beacon-macos binary to package. If omitted, PyInstaller build runs.",
    )
    parser.add_argument(
        "--skip-binary-build",
        action="store_true",
        help="Use dist-binaries/beacon-macos and fail if it is missing.",
    )
    parser.add_argument("--version", help="Package version. Defaults to pyproject.toml.")
    parser.add_argument(
        "--identifier",
        default=DEFAULT_IDENTIFIER,
        help=f"macOS package identifier. Default: {DEFAULT_IDENTIFIER}",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for final .pkg output.",
    )
    parser.add_argument(
        "--sign-identity",
        help="Developer ID Installer identity used by productbuild signing.",
    )
    parser.add_argument(
        "--notarize",
        action="store_true",
        help="Submit the signed package to Apple notarization and staple it.",
    )
    parser.add_argument("--apple-id", help="Apple ID used for notarization.")
    parser.add_argument("--apple-team-id", help="Apple Developer Team ID.")
    parser.add_argument(
        "--apple-password",
        help="Apple app-specific password used by notarytool.",
    )
    return parser.parse_args()


def main():
    try:
        build_pkg(parse_args())
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
