#!/usr/bin/env python3
"""Generate the Live Smoke readiness JSON artifact and Markdown summary."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class Check:
    """One readiness check in the Live Smoke report."""

    name: str
    category: str
    required: bool
    status: str
    job_result: str
    configured: bool
    detail: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "category": self.category,
            "required": self.required,
            "status": self.status,
            "job_result": self.job_result,
            "configured": self.configured,
            "detail": self.detail,
        }


def _flag(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "").lower() == "true"


def build_report(env: Mapping[str, str]) -> dict[str, object]:
    """Build a structured readiness report from GitHub Actions job outputs.

    ``REQUIRE_LIVE_BACKENDS`` requires all three live backends. The per-backend
    flags ``REQUIRE_FOUNDRY`` / ``REQUIRE_FABRIC`` / ``REQUIRE_DATABRICKS`` let a
    facilitator require only the data platform their workshop actually uses, so a
    missing Databricks secret never fails a Fabric-only run (and vice versa).
    """

    require_live = _flag(env, "REQUIRE_LIVE_BACKENDS")
    require_foundry = require_live or _flag(env, "REQUIRE_FOUNDRY")
    require_fabric = require_live or _flag(env, "REQUIRE_FABRIC")
    require_databricks = require_live or _flag(env, "REQUIRE_DATABRICKS")
    any_required = require_foundry or require_fabric or require_databricks
    checks: list[Check] = []

    checks.append(
        _gated_check(
            "Foundry agent registration",
            env.get("FOUNDRY_RESULT", ""),
            env.get("FOUNDRY_CONFIGURED", ""),
            "Set AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID, FOUNDRY_PROJECT_ENDPOINT, "
            "MODEL_DEPLOYMENT_NAME to run.",
            required=require_foundry,
        )
    )
    checks.append(
        _gated_check(
            "Fabric golden-QA live eval",
            env.get("FABRIC_RESULT", ""),
            env.get("FABRIC_CONFIGURED", ""),
            "Set Azure auth plus FABRIC_MCP_URL (or FABRIC_WORKSPACE_ID + FABRIC_DATA_AGENT_ID) to run.",
            required=require_fabric,
        )
    )
    checks.append(
        _gated_check(
            "Databricks Genie query",
            env.get("DATABRICKS_RESULT", ""),
            env.get("DATABRICKS_CONFIGURED", ""),
            "Set DATABRICKS_GENIE_MCP_URL for managed MCP, or DATABRICKS_WORKSPACE_URL and "
            "DATABRICKS_GENIE_SPACE_ID for SDK-direct.",
            required=require_databricks,
        )
    )
    checks.append(_always_check("Published workshop site", env.get("PUBLISHED_RESULT", "")))
    checks.append(_always_check("Offline eval and demo readiness", env.get("READINESS_RESULT", "")))

    failed = sum(1 for check in checks if check.status == "failed" or (check.required and check.status == "skipped"))
    skipped = sum(1 for check in checks if check.status == "skipped")
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "required" if any_required else "demo",
        "live_backend_skips_fail_workflow": any_required,
        "required_backends": {
            "foundry": require_foundry,
            "fabric": require_fabric,
            "databricks": require_databricks,
        },
        "totals": {"failed": failed, "skipped": skipped, "checks": len(checks)},
        "checks": [check.to_dict() for check in checks],
    }


def render_summary(report: Mapping[str, object]) -> str:
    """Render the report as GitHub Step Summary Markdown."""

    totals = report["totals"]
    assert isinstance(totals, Mapping)
    checks = report["checks"]
    assert isinstance(checks, list)
    status_icon = {"ran": "RAN", "failed": "FAILED", "skipped": "SKIPPED"}
    mode = "Required live backends" if report["mode"] == "required" else "Demo / best-effort live backends"
    lines = [
        "# Live Smoke summary",
        "",
        f"**Mode:** {mode}",
        "",
        "| Check | Status | Required | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for check in checks:
        assert isinstance(check, Mapping)
        status = str(check["status"])
        lines.append(
            f"| {check['name']} | {status_icon[status]} | {'yes' if check['required'] else 'no'} | {check['detail']} |"
        )
    lines.extend(["", f"**Totals:** {totals['failed']} failed, {totals['skipped']} skipped."])
    if totals["skipped"]:
        lines.extend(
            [
                "",
                "> Skipped live backend checks mean that backend was not proven by this run.",
                "> Use required mode for pre-customer validation once secrets are configured.",
            ]
        )
    return "\n".join(lines) + "\n"


def _gated_check(name: str, result: str, configured: str, hint: str, *, required: bool) -> Check:
    if result == "failure":
        status = "failed"
        detail = "Live check ran and failed."
    elif result == "cancelled":
        status = "skipped"
        detail = "Job cancelled before completion."
    elif configured == "true":
        status = "ran"
        detail = "Required secrets present; live path executed."
    else:
        status = "skipped"
        detail = hint
        print(f"::warning title={name} skipped::{hint}")
        if required:
            print(f"::error title={name} required::Live backend is required but not configured.")
    return Check(
        name=name,
        category="live-backend",
        required=required,
        status=status,
        job_result=result,
        configured=configured == "true",
        detail=detail,
    )


def _always_check(name: str, result: str) -> Check:
    if result == "success":
        status = "ran"
        detail = "Executed on every run (no secrets required)."
    elif result == "failure":
        status = "failed"
        detail = "Unconditional check failed."
    else:
        status = "skipped"
        detail = f"Job did not complete (result: {result})."
    return Check(
        name=name,
        category="offline-or-public",
        required=True,
        status=status,
        job_result=result,
        configured=True,
        detail=detail,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a Live Smoke demo readiness report.")
    parser.add_argument("--output", type=Path, default=Path("demo-readiness-report.json"))
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path(os.environ["GITHUB_STEP_SUMMARY"]) if os.environ.get("GITHUB_STEP_SUMMARY") else None,
    )
    parser.add_argument(
        "--github-output",
        type=Path,
        default=Path(os.environ["GITHUB_OUTPUT"]) if os.environ.get("GITHUB_OUTPUT") else None,
    )
    args = parser.parse_args(argv)

    report = build_report(os.environ)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = render_summary(report)
    if args.summary is not None:
        args.summary.write_text(summary, encoding="utf-8")
    else:
        print(summary)
    if args.github_output is not None:
        totals = report["totals"]
        assert isinstance(totals, Mapping)
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"failures={totals['failed']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
