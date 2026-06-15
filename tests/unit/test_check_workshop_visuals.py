"""Unit tests for workshop visual proof validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import check_workshop_visuals


def test_validate_workshop_assets_requires_svg_metadata(tmp_path: Path) -> None:
    good = tmp_path / "good.svg"
    good.write_text("<svg><title>Title</title><desc>Description</desc></svg>", encoding="utf-8")

    assets = check_workshop_visuals.validate_workshop_assets((good,))

    assert assets == [{"path": str(good), "bytes": good.stat().st_size}]


def test_validate_workshop_assets_rejects_missing_description(tmp_path: Path) -> None:
    bad = tmp_path / "bad.svg"
    bad.write_text("<svg><title>Title</title></svg>", encoding="utf-8")

    with pytest.raises(ValueError):
        check_workshop_visuals.validate_workshop_assets((bad,))


def test_validate_generated_artifacts_requires_all_formats(tmp_path: Path) -> None:
    for fmt in ("xlsx", "html", "pdf"):
        (tmp_path / f"tailspin_toys_base_quota_estimate.{fmt}").write_bytes(b"proof")

    artifacts = check_workshop_visuals.validate_generated_artifacts(tmp_path)

    assert [artifact["format"] for artifact in artifacts] == ["html", "pdf", "xlsx"]


def test_build_visual_proof_can_check_existing_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    assets = tuple(asset_dir / name for name in ("cli.svg", "artifacts.svg", "foundry.svg"))
    for asset in assets:
        asset.write_text("<svg><title>Title</title><desc>Description</desc></svg>", encoding="utf-8")
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    for fmt in ("xlsx", "html", "pdf"):
        (artifact_dir / f"tailspin_toys_base_quota_estimate.{fmt}").write_bytes(b"proof")
    output_path = tmp_path / "proof.json"
    monkeypatch.setattr(check_workshop_visuals, "WORKSHOP_ASSETS", assets)

    manifest = check_workshop_visuals.build_visual_proof(
        output_path=output_path,
        artifact_dir=artifact_dir,
        skip_generate=True,
    )

    assert manifest["portal_visual"]["type"] == "schematic"
    assert json.loads(output_path.read_text(encoding="utf-8"))["generated_artifacts"][0]["format"] == "html"
