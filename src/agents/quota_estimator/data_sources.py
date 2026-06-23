"""Data-source normalization for quota-estimator sales rows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

DataPlatform = Literal["fabric", "databricks"]


@dataclass(frozen=True)
class SalesDataSource:
    """Display metadata for the platform that supplied quota-estimator rows."""

    platform: DataPlatform
    display_name: str
    query_surface: str
    citation: str


_DATA_SOURCES: dict[DataPlatform, SalesDataSource] = {
    "fabric": SalesDataSource(
        platform="fabric",
        display_name="Microsoft Fabric",
        query_surface="Fabric Data Agent",
        citation=(
            "Microsoft Fabric Data Agent query over sales data (SalesOrderHeader joined to SalesTerritory)."
        ),
    ),
    "databricks": SalesDataSource(
        platform="databricks",
        display_name="Databricks",
        query_surface="Databricks Genie Space backed by Unity Catalog",
        citation="Databricks Genie query over Unity Catalog sales tables.",
    ),
}

_PLATFORM_ALIASES: dict[str, DataPlatform] = {
    "fabric": "fabric",
    "microsoft fabric": "fabric",
    "fabric data agent": "fabric",
    "fabric iq": "fabric",
    "databricks": "databricks",
    "databricks genie": "databricks",
    "genie": "databricks",
    "unity catalog": "databricks",
}

_DATABRICKS_HINT_FIELDS = frozenset(
    {
        "sales_territory",
        "salesTerritory",
        "territory_name_uc",
        "orderDate",
        "order_timestamp",
        "orderTimestamp",
        "net_sales_amount",
        "gross_sales_amount",
        "salesAmount",
        "extendedAmount",
        "units_sold",
        "sold_quantity",
        "quantitySold",
        "source_platform",
        "_source_platform",
    }
)


def resolve_sales_data_source(
    data_source: str | None,
    rows: Sequence[Mapping[str, object]] | None = None,
) -> SalesDataSource:
    """Return source metadata from an explicit source name or row hints."""

    if data_source is not None:
        normalized = data_source.strip().lower()
        if normalized in _PLATFORM_ALIASES:
            return _DATA_SOURCES[_PLATFORM_ALIASES[normalized]]
        allowed = ", ".join(sorted(_DATA_SOURCES))
        raise ValueError(f"Unsupported sales data source '{data_source}'. Allowed values: {allowed}.")

    if rows:
        for row in rows:
            platform_value = row.get("source_platform") or row.get("_source_platform")
            if isinstance(platform_value, str):
                normalized = platform_value.strip().lower()
                if normalized in _PLATFORM_ALIASES:
                    return _DATA_SOURCES[_PLATFORM_ALIASES[normalized]]
            if _DATABRICKS_HINT_FIELDS.intersection(row):
                return _DATA_SOURCES["databricks"]

    return _DATA_SOURCES["fabric"]


def sales_data_sources() -> tuple[SalesDataSource, ...]:
    """Return the supported sales data sources in stable display order."""

    return (_DATA_SOURCES["fabric"], _DATA_SOURCES["databricks"])
