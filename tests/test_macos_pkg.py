import hashlib
import subprocess
import sys

from scripts import build_macos_pkg


def test_macos_pkg_version_comes_from_pyproject():
    assert build_macos_pkg.read_version() == "0.1.2"


def test_macos_pkg_checksum_helper(tmp_path):
    payload = tmp_path / "beacon.pkg"
    payload.write_bytes(b"beacon installer")

    assert build_macos_pkg.sha256_file(payload) == hashlib.sha256(b"beacon installer").hexdigest()


def test_macos_pkg_help_mentions_installer_options():
    result = subprocess.run(
        [sys.executable, "scripts/build_macos_pkg.py", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Build Beacon macOS .pkg installer" in result.stdout
    assert "--binary-path" in result.stdout
    assert "--skip-binary-build" in result.stdout
    assert "--identifier" in result.stdout


def test_release_workflow_publishes_macos_pkg():
    workflow = build_macos_pkg.ROOT.joinpath(".github/workflows/release.yml").read_text(
        encoding="utf-8"
    )

    assert "python scripts/build_macos_pkg.py --skip-binary-build" in workflow
    assert "dist-binaries/*.pkg" in workflow
    assert "release-artifacts/beacon-macos/*.pkg" in workflow


def test_package_script_exposes_macos_pkg_command():
    package_script = build_macos_pkg.ROOT.joinpath("scripts/package.sh").read_text(encoding="utf-8")

    assert "macos-pkg" in package_script
    assert "python3 scripts/build_macos_pkg.py" in package_script
