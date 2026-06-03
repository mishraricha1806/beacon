import subprocess
import sys


def test_module3_flow_release_gate_passes():
    result = subprocess.run(
        [sys.executable, "scripts/module3_flow_check.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Module 3 flow checks passed" in result.stdout
