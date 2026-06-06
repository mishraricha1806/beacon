#!/usr/bin/env python3
"""
Build standalone Beacon binaries using PyInstaller.
Supports macOS, Linux, and Windows.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def get_version():
    version_file = Path(__file__).parent / "VERSION"

    if version_file.exists():
        return version_file.read_text().strip()

    pyproject_file = Path(__file__).parent.parent / "pyproject.toml"

    if pyproject_file.exists():
        for line in pyproject_file.read_text().splitlines():
            if line.strip().startswith("version"):
                return line.split("=", 1)[1].strip().strip('"')

    return "0.0.0"

def build_binary(platform: str, output_name: str):
    """Build a standalone binary for the specified platform."""
    print(f"\n{'='*60}")
    print(f"Building Beacon for {platform}...")
    print(f"{'='*60}\n")

    version = get_version()
    dist_dir = Path("dist-binaries")
    dist_dir.mkdir(exist_ok=True)

    # PyInstaller arguments
    pyinstaller_args = [
        "pyinstaller",
        "--onefile",
        "--name", output_name,
        "--distpath", str(dist_dir),
        "--workpath", f"build/{platform}",
        "--specpath", f"build/{platform}",
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
        "beacon/cli.py",
    ]

    # Platform-specific options
    if sys.platform == "darwin":
        pyinstaller_args.extend([
            "--osx-bundle-identifier=ai.beacon.cli",
            "--codesign-identity=-",  # Ad-hoc sign
        ])

    # Run PyInstaller
    result = subprocess.run(pyinstaller_args, capture_output=False)

    if result.returncode != 0:
        print(f"\n❌ Build failed for {platform}")
        return False

    binary_path = dist_dir / output_name
    if sys.platform != "win32":
        os.chmod(binary_path, 0o755)

    print(f"\n✅ Build successful for {platform}")
    print(f"   Binary: {binary_path}")
    return True

def create_checksums(dist_dir: Path):
    """Create SHA256 checksums for all binaries."""
    import hashlib

    checksums_file = dist_dir / "CHECKSUMS.txt"
    checksums = []

    for binary in dist_dir.glob("beacon*"):
        if binary.is_file():
            sha256_hash = hashlib.sha256()
            with open(binary, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            checksum = sha256_hash.hexdigest()
            checksums.append(f"{checksum}  {binary.name}")
            print(f"   {binary.name}: {checksum}")

    checksums_file.write_text("\n".join(checksums))
    print(f"\nChecksums saved to: {checksums_file}")

def main():
    """Main build function."""
    print(f"Beacon Binary Builder v{get_version()}")
    print("=" * 60)

    # Determine which platforms to build
    platforms_to_build = []
    if len(sys.argv) > 1:
        platforms_to_build = sys.argv[1:]
    else:
        # Build for current platform
        if sys.platform == "darwin":
            platforms_to_build = ["macos"]
        elif sys.platform == "linux":
            platforms_to_build = ["linux"]
        elif sys.platform == "win32":
            platforms_to_build = ["windows"]

    platform_map = {
        "macos": "beacon-macos",
        "linux": "beacon-linux",
        "windows": "beacon-windows.exe",
    }

    failed = []
    for platform in platforms_to_build:
        if platform not in platform_map:
            print(f"❌ Unknown platform: {platform}")
            print(f"   Supported: {', '.join(platform_map.keys())}")
            continue

        output_name = platform_map[platform]
        if not build_binary(platform, output_name):
            failed.append(platform)

    # Create checksums
    dist_dir = Path("dist-binaries")
    if dist_dir.exists():
        print("\n" + "="*60)
        print("Creating SHA256 checksums...")
        print("="*60)
        create_checksums(dist_dir)

    # Summary
    print("\n" + "="*60)
    print("Build Summary")
    print("="*60)

    if failed:
        print(f"❌ Failed platforms: {', '.join(failed)}")
        return 1
    else:
        print("✅ All binaries built successfully!")
        print(f"   Output directory: {dist_dir.absolute()}")
        return 0

if __name__ == "__main__":
    sys.exit(main())

