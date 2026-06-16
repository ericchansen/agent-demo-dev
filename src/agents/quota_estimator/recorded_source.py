"""Recorded (offline) backend sales sources for end-to-end proof.

These adapters replay non-secret, backend-shaped Wide World Importers fixtures
through the SAME normalization, quota-calculation, and report-generation code
path that the live Fabric and Databricks backends feed. They prove the
``rows -> normalize -> quota -> XLSX/HTML/PDF`` path end to end WITHOUT any
network access or secrets.

They are deliberately NOT a substitute for live-backend validation: no Fabric
or Databricks round trip happens here, so a passing recorded proof must never be
reported as a live backend being "proven". Live-backend checks stay gated on real
secrets elsewhere (see ``scripts/live_smoke_report.py``).
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from src.agents.quota_estimator.data_sources import (
    DataPlatform,
    SalesDataSource,
    resolve_sales_data_source,
)

RECORDED_FIXTURES_DIR = Path(__file__).resolve().parent / "recorded_fixtures"

_FIXTURE_FILES: dict[DataPlatform, str] = {
    "fabric": "fabric_wwi_sales.json",
    "databricks": "databricks_wwi_sales.json",
}


class RecordedFixtureError(RuntimeError):
    """Raised when a recorded backend fixture is missing or malformed."""


@dataclass(frozen=True)
class RecordedSalesSource:
    """A non-secret, backend-shaped sales fixture replayed through the real pipeline."""

    platform: DataPlatform
    fixture_path: Path

    @property
    def fixture(self) -> Mapping[str, object]:
        if not self.fixture_path.is_file():
            raise RecordedFixtureError(f"Recorded fixture not found: {self.fixture_path}")
        try:
            data = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RecordedFixtureError(f"Recorded fixture is not valid JSON: {self.fixture_path}") from exc
        if not isinstance(data, Mapping):
            raise RecordedFixtureError(f"Recorded fixture must be a JSON object: {self.fixture_path}")
        return data

    @property
    def description(self) -> str:
        return str(self.fixture.get("description", ""))

    def load_rows(self) -> list[dict[str, object]]:
        """Return a deep copy of the backend-shaped rows from the fixture."""

        rows = self.fixture.get("rows")
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
            raise RecordedFixtureError(f"Recorded fixture '{self.fixture_path}' has no 'rows' array.")
        normalized: list[dict[str, object]] = []
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                raise RecordedFixtureError(f"Recorded fixture row {index} in '{self.fixture_path}' is not an object.")
            normalized.append(copy.deepcopy(dict(row)))
        if not normalized:
            raise RecordedFixtureError(f"Recorded fixture '{self.fixture_path}' has an empty 'rows' array.")
        return normalized

    def display_source(self) -> SalesDataSource:
        """Resolve the display metadata the pipeline attaches for this platform."""

        return resolve_sales_data_source(self.platform)


def recorded_sales_source(platform: DataPlatform) -> RecordedSalesSource:
    """Return the recorded sales source for a single supported platform."""

    if platform not in _FIXTURE_FILES:
        allowed = ", ".join(sorted(_FIXTURE_FILES))
        raise RecordedFixtureError(f"Unsupported recorded platform '{platform}'. Allowed values: {allowed}.")
    return RecordedSalesSource(platform=platform, fixture_path=RECORDED_FIXTURES_DIR / _FIXTURE_FILES[platform])


def recorded_sales_sources() -> tuple[RecordedSalesSource, ...]:
    """Return every recorded sales source in stable platform order."""

    platforms: tuple[DataPlatform, ...] = ("fabric", "databricks")
    return tuple(recorded_sales_source(platform) for platform in platforms)


def load_recorded_rows(platform: DataPlatform) -> list[dict[str, object]]:
    """Convenience helper returning the backend-shaped rows for a platform."""

    return recorded_sales_source(platform).load_rows()
