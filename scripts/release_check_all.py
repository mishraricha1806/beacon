#!/usr/bin/env python3
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_step(name, command):
    started = time.monotonic()
    print(f"\n== {name} ==")
    print(" ".join(command))
    result = subprocess.run(command, cwd=ROOT)
    elapsed = time.monotonic() - started

    if result.returncode != 0:
        print(f"FAIL: {name} failed after {elapsed:.2f}s", file=sys.stderr)
        return result.returncode

    print(f"ok: {name} completed in {elapsed:.2f}s")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Run all Beacon release checks.")
    parser.add_argument(
        "--require-helm",
        action="store_true",
        help="Pass --require-helm to the Module 1 release gate.",
    )
    parser.add_argument(
        "--skip-pytest",
        action="store_true",
        help="Skip the full pytest suite. Useful only for focused local debugging.",
    )
    parser.add_argument(
        "--skip-ui",
        action="store_true",
        help="Skip UI smoke checks. Useful in restricted sandboxes that cannot bind localhost.",
    )
    parser.add_argument(
        "--skip-diff-check",
        action="store_true",
        help="Skip git diff --check. Useful outside a git checkout.",
    )
    args = parser.parse_args()

    python = sys.executable
    module1 = [python, "scripts/module1_release_check.py"]
    if args.require_helm:
        module1.append("--require-helm")

    steps = [("Module 1 release gate", module1)]

    if not args.skip_ui:
        steps.append(("UI smoke gate", [python, "scripts/ui_smoke_check.py"]))

    steps.extend(
        [
            ("Module 2 diagnostic gate", [python, "scripts/module2_diagnostic_check.py"]),
            ("Module 3 flow gate", [python, "scripts/module3_flow_check.py"]),
            ("Module 4 decision gate", [python, "scripts/module4_decision_check.py"]),
        ]
    )

    if not args.skip_pytest:
        steps.append(("Full pytest suite", [python, "-m", "pytest", "-q"]))

    if not args.skip_diff_check:
        steps.append(("Git diff hygiene", ["git", "diff", "--check"]))

    started = time.monotonic()
    for name, command in steps:
        result = run_step(name, command)
        if result != 0:
            return result

    print(f"\nAll Beacon release checks passed in {time.monotonic() - started:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
