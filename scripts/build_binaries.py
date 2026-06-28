#!/usr/bin/env python3
"""
Build standalone Beacon binaries using PyInstaller.
Supports macOS, Linux, and Windows.
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent


def get_version():
    version_file = Path(__file__).parent / "VERSION"

    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()

    pyproject_file = ROOT / "pyproject.toml"

    if pyproject_file.exists():
        for line in pyproject_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("version"):
                return line.split("=", 1)[1].strip().strip('"')

    return "0.0.0"


def build_binary(platform: str, output_name: str):
    """Build a standalone binary for the specified platform."""
    print(f"\n{'=' * 60}")
    print(f"Building Beacon for {platform}...")
    print(f"{'=' * 60}\n")

    dist_dir = Path("dist-binaries")
    dist_dir.mkdir(exist_ok=True)

    pyinstaller_args = [
        "pyinstaller",
        "--onefile",
        "--name",
        output_name,
        "--distpath",
        str(dist_dir),
        "--workpath",
        f"build/{platform}",
        "--specpath",
        f"build/{platform}",
        "--hidden-import=beacon",
        "--hidden-import=beacon.cli",
        "--hidden-import=beacon.scanner",
        "--hidden-import=beacon.reporter",
        "--hidden-import=beacon.engine",
        "--hidden-import=beacon.rules",
        "--hidden-import=beacon.readiness",
        "--hidden-import=beacon.diagnose",
        "--hidden-import=beacon.intelligence",
        "--collect-all=beacon",
        "--collect-data=hcl2",
        "beacon/cli.py",
    ]

    packs_path = ROOT / "packs"
    if packs_path.exists():
        pyinstaller_args.insert(-1, f"--add-data={packs_path}{os.pathsep}packs")

    if sys.platform == "darwin":
        pyinstaller_args.extend(
            [
                "--osx-bundle-identifier=ai.beacon.cli",
                "--codesign-identity=-",
            ]
        )

    result = subprocess.run(pyinstaller_args, check=False)

    if result.returncode != 0:
        print(f"\n[ERROR] Build failed for {platform}")
        return False

    binary_path = dist_dir / output_name

    if not binary_path.exists():
        print(f"\n[ERROR] Expected binary was not created: {binary_path}")
        return False

    if sys.platform != "win32":
        os.chmod(binary_path, 0o755)

    print(f"\n[OK] Build successful for {platform}")
    print(f"     Binary: {binary_path}")

    return True


def create_checksums(dist_dir: Path):
    """Create SHA256 checksums for all binaries."""
    checksums_file = dist_dir / "CHECKSUMS.txt"
    checksums = []

    for binary in sorted(dist_dir.glob("beacon*")):
        if not binary.is_file():
            continue

        sha256_hash = hashlib.sha256()

        with open(binary, "rb") as file:
            for chunk in iter(lambda: file.read(4096), b""):
                sha256_hash.update(chunk)

        checksum = sha256_hash.hexdigest()
        checksums.append(f"{checksum}  {binary.name}")
        print(f"     {binary.name}: {checksum}")

    checksums_file.write_text("\n".join(checksums), encoding="utf-8")
    print(f"\nChecksums saved to: {checksums_file}")


def resolve_platforms():
    """Resolve requested platforms."""
    if len(sys.argv) > 1:
        return sys.argv[1:]

    if sys.platform == "darwin":
        return ["macos"]

    if sys.platform == "linux":
        return ["linux"]

    if sys.platform == "win32":
        return ["windows"]

    return []


def main():
    """Main build function."""
    print(f"Beacon Binary Builder v{get_version()}")
    print("=" * 60)

    platforms_to_build = resolve_platforms()

    if not platforms_to_build:
        print("[ERROR] Could not determine platform to build.")
        return 1

    platform_map = {
        "macos": "beacon-macos",
        "linux": "beacon-linux",
        "windows": "beacon-windows.exe",
    }

    failed = []

    for platform in platforms_to_build:
        if platform not in platform_map:
            print(f"[ERROR] Unknown platform: {platform}")
            print(f"        Supported: {', '.join(platform_map.keys())}")
            failed.append(platform)
            continue

        output_name = platform_map[platform]

        if not build_binary(platform, output_name):
            failed.append(platform)

    dist_dir = Path("dist-binaries")

    if dist_dir.exists():
        print("\n" + "=" * 60)
        print("Creating SHA256 checksums...")
        print("=" * 60)
        create_checksums(dist_dir)

    print("\n" + "=" * 60)
    print("Build Summary")
    print("=" * 60)

    if failed:
        print(f"[ERROR] Failed platforms: {', '.join(failed)}")
        return 1

    print("[OK] All binaries built successfully!")
    print(f"     Output directory: {dist_dir.absolute()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
