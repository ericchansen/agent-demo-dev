#!/usr/bin/env python3
"""Validate workshop visuals and capture a local artifact proof manifest."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.orchestrator.multi_agent import run_multi_agent_pipeline  # noqa: E402

WORKSHOP_ASSETS = (
    ROOT / "website" / "static" / "img" / "workshop" / "cli-report-flow.svg",
    ROOT / "website" / "static" / "img" / "workshop" / "quota-artifacts.svg",
    ROOT / "website" / "static" / "img" / "workshop" / "foundry-playground.svg",
)
EXPECTED_FORMATS = {"xlsx", "html", "pdf"}


def build_visual_proof(
    *,
    output_path: Path,
    artifact_dir: Path,
    skip_generate: bool = False,
) -> dict[str, object]:
    """Generate/check local proof artifacts and return a JSON-serializable manifest."""

    assets = validate_workshop_assets(WORKSHOP_ASSETS)
    pipeline_result: dict[str, object] | None = None
    if not skip_generate:
        pipeline_result = run_multi_agent_pipeline(
            "Generate a quota report for Tailspin Toys",
            customer_name="Tailspin Toys",
            data_source="fabric",
            output_dir=artifact_dir,
        )
    generated_artifacts = validate_generated_artifacts(artifact_dir)
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "command": (
            "uv run python -m src.orchestrator.multi_agent "
            '"Generate a quota report for Tailspin Toys" --customer "Tailspin Toys" --data-source fabric'
        ),
        "visual_assets": assets,
        "generated_artifacts": generated_artifacts,
        "pipeline_response": str(pipeline_result.get("response", "")) if pipeline_result else None,
        "portal_visual": {
            "path": _relative(WORKSHOP_ASSETS[2]),
            "type": "schematic",
            "reason": (
                "Authenticated Foundry Playground screenshots must be captured manually in the facilitator tenant."
            ),
            "manual_checklist": [
                "Open https://ai.azure.com and select fsa-foundry-project-dev.",
                "Open Agents > WWISalesAgent > Playground.",
                "Run Generate a quota report for Tailspin Toys.",
                "Capture Playground answer and trace/tool-call metadata with customer data redacted.",
            ],
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def validate_workshop_assets(paths: tuple[Path, ...] = WORKSHOP_ASSETS) -> list[dict[str, object]]:
    """Validate that static workshop visuals exist and include accessible SVG metadata."""

    assets: list[dict[str, object]] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Missing workshop visual asset: {_relative(path)}")
        text = path.read_text(encoding="utf-8")
        if "<title" not in text or "<desc" not in text:
            raise ValueError(f"Workshop visual asset is missing SVG title/desc metadata: {_relative(path)}")
        assets.append({"path": _relative(path), "bytes": path.stat().st_size})
    return assets


def validate_generated_artifacts(artifact_dir: Path) -> list[dict[str, object]]:
    """Validate generated Tailspin Toys XLSX/HTML/PDF proof artifacts."""

    artifacts: list[dict[str, object]] = []
    missing: set[str] = set()
    for fmt in sorted(EXPECTED_FORMATS):
        matches = sorted(artifact_dir.glob(f"tailspin_toys_*_quota_estimate.{fmt}"))
        if not matches:
            missing.add(fmt)
            continue
        path = matches[-1]
        if path.stat().st_size <= 0:
            raise ValueError(f"Generated {fmt} artifact is empty: {_relative(path)}")
        artifacts.append({"format": fmt, "path": _relative(path), "bytes": path.stat().st_size})
    if missing:
        raise FileNotFoundError(f"Missing generated artifact formats in {_relative(artifact_dir)}: {sorted(missing)}")
    return artifacts


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate workshop visuals and local proof artifacts.")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "workshop-visual-proof.json")
    parser.add_argument("--artifact-dir", type=Path, default=ROOT / "output" / "workshop-visual-proof")
    parser.add_argument("--skip-generate", action="store_true", help="Only validate artifacts already on disk.")
    args = parser.parse_args(argv)

    manifest = build_visual_proof(
        output_path=args.output,
        artifact_dir=args.artifact_dir,
        skip_generate=args.skip_generate,
    )
    print(f"Validated {len(manifest['visual_assets'])} visual assets.")
    print(f"Validated {len(manifest['generated_artifacts'])} generated artifacts.")
    print(f"Wrote {_relative(args.output)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
