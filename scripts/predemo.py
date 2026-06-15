#!/usr/bin/env python3
"""Run the full local pre-demo validation path."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBSITE = ROOT / "website"


@dataclass(frozen=True)
class StepResult:
    name: str
    command: str
    passed: bool
    elapsed: float
    output: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all pre-demo checks.")
    parser.add_argument("--azure", action="store_true", help="Include live Azure checks in scripts/demo_check.py.")
    parser.add_argument("--docker", action="store_true", help="Include Docker hosted-agent smoke checks.")
    args = parser.parse_args()

    python = sys.executable
    demo_check = [python, "scripts\\demo_check.py"]
    if args.azure:
        demo_check.append("--azure")
    if args.docker:
        demo_check.append("--docker")

    steps: list[tuple[str, list[str], Path]] = [
        ("Sync dependencies", ["uv", "sync", "--extra", "dev"], ROOT),
        ("Ruff lint", [python, "-m", "ruff", "check", "."], ROOT),
        ("Ruff format", [python, "-m", "ruff", "format", "--check", "."], ROOT),
        ("Mypy", [python, "-m", "mypy", "src\\"], ROOT),
        ("Unit tests", [python, "-m", "pytest", "tests\\unit\\"], ROOT),
        ("Golden QA eval", [python, "tests\\eval\\run_eval.py", "--mock", "--pass-rate", "100"], ROOT),
        ("Demo readiness", demo_check, ROOT),
        ("Website build", [_tool("npm"), "run", "build"], WEBSITE),
    ]

    results: list[StepResult] = []
    for name, command, cwd in steps:
        result = _run_step(name, command, cwd)
        results.append(result)
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {name} ({result.elapsed:.1f}s)")
        if not result.passed:
            print(f"Command: {result.command}")
            if result.output:
                print(result.output)
            break

    print("\nPre-demo summary")
    print("----------------")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status:4s} {result.name:<18s} {result.elapsed:>6.1f}s")

    return 0 if results and all(result.passed for result in results) and len(results) == len(steps) else 1


def _run_step(name: str, command: list[str], cwd: Path) -> StepResult:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as exc:
        elapsed = time.monotonic() - started
        return StepResult(
            name=name,
            command=_format_command(command, cwd),
            passed=False,
            elapsed=elapsed,
            output=f"Executable not found: {exc.filename}",
        )
    elapsed = time.monotonic() - started
    output = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part)
    return StepResult(
        name=name,
        command=_format_command(command, cwd),
        passed=completed.returncode == 0,
        elapsed=elapsed,
        output=output,
    )


def _format_command(command: list[str], cwd: Path) -> str:
    prefix = "" if cwd == ROOT else f"cd {cwd.relative_to(ROOT)} && "
    return prefix + " ".join(command)


def _tool(name: str) -> str:
    if sys.platform == "win32":
        cmd_path = shutil.which(f"{name}.cmd")
        if cmd_path:
            return cmd_path
    return shutil.which(name) or name


if __name__ == "__main__":
    sys.exit(main())
