"""Unit tests for Live Smoke readiness report generation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.live_smoke_report import build_report, main, render_summary


def test_build_report_demo_mode_marks_unconfigured_live_backends_skipped() -> None:
    report = build_report(
        {
            "REQUIRE_LIVE_BACKENDS": "false",
            "FOUNDRY_RESULT": "success",
            "FOUNDRY_CONFIGURED": "false",
            "FABRIC_RESULT": "success",
            "FABRIC_CONFIGURED": "false",
            "DATABRICKS_RESULT": "success",
            "DATABRICKS_CONFIGURED": "false",
            "PUBLISHED_RESULT": "success",
            "READINESS_RESULT": "success",
        }
    )

    assert report["mode"] == "demo"
    assert report["totals"]["failed"] == 0
    assert report["totals"]["skipped"] == 3
    live_checks = [check for check in report["checks"] if check["category"] == "live-backend"]
    assert {check["status"] for check in live_checks} == {"skipped"}
    assert not any(check["required"] for check in live_checks)


def test_build_report_required_mode_fails_skipped_live_backends() -> None:
    report = build_report(
        {
            "REQUIRE_LIVE_BACKENDS": "true",
            "FOUNDRY_RESULT": "success",
            "FOUNDRY_CONFIGURED": "false",
            "FABRIC_RESULT": "success",
            "FABRIC_CONFIGURED": "false",
            "DATABRICKS_RESULT": "success",
            "DATABRICKS_CONFIGURED": "true",
            "PUBLISHED_RESULT": "success",
            "READINESS_RESULT": "success",
        }
    )

    assert report["mode"] == "required"
    assert report["totals"]["failed"] == 2
    assert report["totals"]["skipped"] == 2
    assert report["checks"][2]["status"] == "ran"


def test_render_summary_includes_mode_and_totals() -> None:
    report = build_report(
        {
            "FOUNDRY_RESULT": "success",
            "FOUNDRY_CONFIGURED": "true",
            "FABRIC_RESULT": "success",
            "FABRIC_CONFIGURED": "true",
            "DATABRICKS_RESULT": "success",
            "DATABRICKS_CONFIGURED": "true",
            "PUBLISHED_RESULT": "success",
            "READINESS_RESULT": "success",
        }
    )

    summary = render_summary(report)

    assert "Demo / best-effort live backends" in summary
    assert "0 failed, 0 skipped" in summary


def test_main_writes_json_summary_and_github_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOUNDRY_RESULT", "success")
    monkeypatch.setenv("FOUNDRY_CONFIGURED", "true")
    monkeypatch.setenv("FABRIC_RESULT", "success")
    monkeypatch.setenv("FABRIC_CONFIGURED", "false")
    monkeypatch.setenv("DATABRICKS_RESULT", "success")
    monkeypatch.setenv("DATABRICKS_CONFIGURED", "false")
    monkeypatch.setenv("PUBLISHED_RESULT", "success")
    monkeypatch.setenv("READINESS_RESULT", "success")
    report_path = tmp_path / "report.json"
    summary_path = tmp_path / "summary.md"
    output_path = tmp_path / "github-output.txt"

    exit_code = main(
        ["--output", str(report_path), "--summary", str(summary_path), "--github-output", str(output_path)]
    )

    assert exit_code == 0
    assert json.loads(report_path.read_text(encoding="utf-8"))["totals"]["skipped"] == 2
    assert "Live Smoke summary" in summary_path.read_text(encoding="utf-8")
    assert output_path.read_text(encoding="utf-8") == "failures=0\n"
