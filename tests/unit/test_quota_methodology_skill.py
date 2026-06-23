"""Guard tests keeping the versioned quota-methodology SKILL.md in sync with the implementation."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agents.quota_estimator.pipeline import _SCENARIO_ADJUSTMENTS

SKILL_PATH = Path(__file__).resolve().parents[2] / "src" / "cli" / "skills" / "quota-methodology" / "SKILL.md"


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_skill_file_exists() -> None:
    assert SKILL_PATH.is_file(), f"Missing versioned skill at {SKILL_PATH}"


def test_skill_declares_name_and_version(skill_text: str) -> None:
    assert "name: quota-methodology" in skill_text
    assert "version: 1.0.0" in skill_text


def test_skill_documents_actual_scenario_adjustments(skill_text: str) -> None:
    assert _SCENARIO_ADJUSTMENTS == {"conservative": -0.03, "base": 0.0, "aggressive": 0.03}
    assert "conservative -0.03" in skill_text
    assert "base 0.0" in skill_text
    assert "aggressive +0.03" in skill_text


def test_skill_documents_core_formula_constants(skill_text: str) -> None:
    assert "0.04 + 0.5 * historical_growth_rate" in skill_text
    assert "-0.05, 0.25" in skill_text
    assert "trailing_revenue * (1 + recommended_growth_rate)" in skill_text


def test_skill_lists_required_tools(skill_text: str) -> None:
    for tool in ("sales-data", "researcher-agent", "workiq", "quota-estimator"):
        assert tool in skill_text
