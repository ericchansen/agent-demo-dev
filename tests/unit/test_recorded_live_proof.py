"""Unit tests for the recorded / offline backend end-to-end proof.

These prove that backend-shaped Wide World Importers fixtures flow through the
real quota pipeline and report renderers, producing normalized recommendations
and non-empty XLSX/HTML/PDF artifacts with source-specific citations and
methodology. They are an OFFLINE proof and never assert a live backend round
trip.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.recorded_live_proof import main, run_all, run_recorded_proof
from src.agents.quota_estimator.recorded_source import (
    RecordedFixtureError,
    load_recorded_rows,
    recorded_sales_source,
    recorded_sales_sources,
)

_FORMATS = ("xlsx", "html", "pdf")


@pytest.mark.parametrize("platform", ["fabric", "databricks"])
def test_recorded_proof_generates_all_artifacts(platform: str, tmp_path: Path) -> None:
    source = recorded_sales_source(platform)  # type: ignore[arg-type]
    result = run_recorded_proof(source, tmp_path)

    assert result["platform"] == platform
    artifacts = result["artifacts"]
    assert isinstance(artifacts, dict)
    assert set(artifacts) == set(_FORMATS)
    for fmt in _FORMATS:
        path = Path(artifacts[fmt])
        assert path.is_file()
        assert path.stat().st_size > 0
        assert path.suffix == f".{fmt}"


def test_fabric_recorded_proof_uses_fabric_citation_and_methodology(tmp_path: Path) -> None:
    source = recorded_sales_source("fabric")
    result = run_recorded_proof(source, tmp_path)

    assert "Microsoft Fabric Data Agent" in result["citation"]
    assert result["query_surface"] == "Fabric Data Agent"
    # The Databricks-specific surface must not leak into a Fabric proof.
    assert "Genie" not in str(result["citation"])


def test_databricks_recorded_proof_uses_databricks_citation_and_methodology(tmp_path: Path) -> None:
    source = recorded_sales_source("databricks")
    result = run_recorded_proof(source, tmp_path)

    assert "Databricks Genie" in result["citation"]
    assert "Unity Catalog" in result["query_surface"]
    assert "Fabric" not in str(result["citation"])


def test_recorded_rows_normalize_into_positive_quota_recommendations(tmp_path: Path) -> None:
    results = run_all(tmp_path)

    assert {result["platform"] for result in results} == {"fabric", "databricks"}
    for result in results:
        assert result["recommendations"] >= 1
        assert isinstance(result["recommended_quota_total"], (int, float))
        assert result["recommended_quota_total"] > 0
        # Both backend fixtures describe the same WWI book of business, so the
        # normalized quota total must agree regardless of column-naming shape.
    totals = {result["platform"]: result["recommended_quota_total"] for result in results}
    assert totals["fabric"] == pytest.approx(totals["databricks"])


def test_recorded_fixtures_carry_source_platform_for_autodetection() -> None:
    fabric_rows = load_recorded_rows("fabric")
    databricks_rows = load_recorded_rows("databricks")

    assert fabric_rows and databricks_rows
    # Databricks rows are self-describing so the pipeline can auto-detect them.
    assert all(row.get("source_platform") == "databricks" for row in databricks_rows)
    # Fabric rows use native PascalCase WWI columns and resolve to Fabric by default.
    assert all("SalesTerritory" in row for row in fabric_rows)

    sources = recorded_sales_sources()
    assert {source.platform for source in sources} == {"fabric", "databricks"}

    with pytest.raises(RecordedFixtureError):
        recorded_sales_source("snowflake")  # type: ignore[arg-type]


def test_recorded_proof_main_exits_zero(tmp_path: Path) -> None:
    exit_code = main(["--output-dir", str(tmp_path), "--json"])
    assert exit_code == 0
