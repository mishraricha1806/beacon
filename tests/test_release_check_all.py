import subprocess
import sys


def test_release_check_all_fast_path_passes():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/release_check_all.py",
            "--skip-pytest",
            "--skip-diff-check",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Module 1 release gate" in result.stdout
    assert "Module 2 diagnostic gate" in result.stdout
    assert "Module 3 flow gate" in result.stdout
    assert "All Beacon release checks passed" in result.stdout
