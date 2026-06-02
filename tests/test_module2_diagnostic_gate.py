import subprocess
import sys


def test_module2_diagnostic_release_gate_passes():
    result = subprocess.run(
        [sys.executable, "scripts/module2_diagnostic_check.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Module 2 diagnostic checks passed" in result.stdout
