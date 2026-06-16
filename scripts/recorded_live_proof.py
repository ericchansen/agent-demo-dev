#!/usr/bin/env python3
"""Recorded / offline backend end-to-end proof for the quota pipeline.

This drives the SAME quota normalization, calculation, and report-generation
code path that the live Fabric and Databricks backends feed -- but using
non-secret, backend-shaped Wide World Importers fixtures instead of a live
round trip. It proves that, given backend-shaped rows, the pipeline produces
normalized quota recommendations and real XLSX/HTML/PDF artifacts with
source-specific citations and methodology.

IMPORTANT: This is an OFFLINE proof. It does NOT contact Fabric or Databricks
and must never be reported as a live backend being "proven". Live-backend
validation stays gated on real secrets (see scripts/live_smoke_report.py).
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agents.quota_estimator.pipeline import (  # noqa: E402
    demo_research_data,
    demo_workiq_activity,
    generate_quota_estimation_report,
)
from src.agents.quota_estimator.recorded_source import (  # noqa: E402
    RecordedSalesSource,
    recorded_sales_sources,
)

_REQUIRED_FORMATS = ("xlsx", "html", "pdf")
# Fixed anchors keep the proof deterministic across runs and machines.
_AS_OF = date(2026, 6, 1)
_GENERATED_AT = datetime(2026, 6, 1, 9, 0, 0)
_CUSTOMER = "Tailspin Toys"


class RecordedProofError(RuntimeError):
    """Raised when a recorded backend proof fails its assertions."""


def run_recorded_proof(source: RecordedSalesSource, output_dir: Path) -> dict[str, object]:
    """Replay one backend fixture through the real pipeline and validate the result."""

    rows = source.load_rows()
    expected = source.display_source()
    platform_dir = output_dir / source.platform
    result = generate_quota_estimation_report(
        customer_name=_CUSTOMER,
        sales_rows=rows,
        research_data=demo_research_data(_CUSTOMER),
        workiq_activity=demo_workiq_activity(_CUSTOMER, as_of=_AS_OF),
        data_source=source.platform,
        scenario="base",
        output_dir=platform_dir,
        formats=_REQUIRED_FORMATS,
        generated_at=_GENERATED_AT,
    )

    if result.get("status") != "success":
        raise RecordedProofError(f"{source.platform}: pipeline returned status {result.get('status')!r}.")

    recommendations = result.get("recommendations")
    if not isinstance(recommendations, list) or not recommendations:
        raise RecordedProofError(f"{source.platform}: pipeline produced no quota recommendations.")
    for rec in recommendations:
        if not rec.get("territory") or not rec.get("category"):
            raise RecordedProofError(f"{source.platform}: a recommendation is missing territory/category.")
        if not isinstance(rec.get("recommended_quota"), (int, float)) or rec["recommended_quota"] <= 0:
            raise RecordedProofError(f"{source.platform}: a recommendation has a non-positive quota.")

    citations = result.get("citations")
    if not isinstance(citations, list) or expected.citation not in citations:
        raise RecordedProofError(
            f"{source.platform}: expected source citation {expected.citation!r} missing from {citations!r}."
        )

    methodology = str(result.get("methodology", ""))
    if expected.query_surface not in methodology:
        raise RecordedProofError(
            f"{source.platform}: methodology does not reference query surface {expected.query_surface!r}."
        )

    artifacts = result.get("artifacts")
    if not isinstance(artifacts, dict):
        raise RecordedProofError(f"{source.platform}: pipeline returned no artifacts mapping.")
    artifact_sizes: dict[str, int] = {}
    for fmt in _REQUIRED_FORMATS:
        raw_path = artifacts.get(fmt)
        if not isinstance(raw_path, str):
            raise RecordedProofError(f"{source.platform}: missing {fmt} artifact.")
        path = Path(raw_path)
        if not path.is_file():
            raise RecordedProofError(f"{source.platform}: {fmt} artifact not written to disk: {path}.")
        size = path.stat().st_size
        if size <= 0:
            raise RecordedProofError(f"{source.platform}: {fmt} artifact is empty: {path}.")
        artifact_sizes[fmt] = size

    return {
        "platform": source.platform,
        "display_name": expected.display_name,
        "query_surface": expected.query_surface,
        "rows": len(rows),
        "recommendations": len(recommendations),
        "recommended_quota_total": result["summary"]["recommended_quota_total"],
        "citation": expected.citation,
        "artifacts": {fmt: str(Path(artifacts[fmt])) for fmt in _REQUIRED_FORMATS},
        "artifact_bytes": artifact_sizes,
    }


def run_all(output_dir: Path) -> list[dict[str, object]]:
    """Run the recorded proof for every supported backend platform."""

    output_dir.mkdir(parents=True, exist_ok=True)
    return [run_recorded_proof(source, output_dir) for source in recorded_sales_sources()]


def _render_text(results: list[dict[str, object]]) -> str:
    lines = [
        "Recorded / offline backend E2E proof (NOT a live backend round trip)",
        "=" * 68,
    ]
    for result in results:
        artifacts = result["artifact_bytes"]
        assert isinstance(artifacts, dict)
        rendered = ", ".join(f"{fmt} {size}B" for fmt, size in artifacts.items())
        lines.append(
            f"PASS {result['display_name']:<18} via {result['query_surface']}: "
            f"{result['rows']} rows -> {result['recommendations']} recommendations; "
            f"artifacts [{rendered}]"
        )
    lines.append("")
    lines.append(
        "These results prove the normalize -> quota -> report path for each backend "
        "shape. They do NOT prove a live Fabric/Databricks connection."
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the recorded / offline backend E2E proof.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for generated artifacts. Defaults to a temporary directory.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of text.")
    args = parser.parse_args(argv)

    output_dir = args.output_dir or Path(tempfile.mkdtemp(prefix="recorded-live-proof-"))
    try:
        results = run_all(output_dir)
    except Exception as exc:  # noqa: BLE001 - surface a clear non-zero failure to CI.
        print(f"::error title=Recorded backend E2E proof::{exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"status": "success", "results": results}, indent=2))
    else:
        print(_render_text(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
