"""Tests for the live backend readiness matrix in demo_check."""

from __future__ import annotations

import pytest

from scripts.demo_check import live_backend_readiness

_ALL_BACKEND_ENV_VARS = (
    "AZURE_CLIENT_ID",
    "AZURE_TENANT_ID",
    "AZURE_SUBSCRIPTION_ID",
    "FOUNDRY_PROJECT_ENDPOINT",
    "MODEL_DEPLOYMENT_NAME",
    "FABRIC_MCP_URL",
    "FABRIC_WORKSPACE_ID",
    "FABRIC_DATA_AGENT_ID",
    "FABRIC_CLIENT_ID",
    "FABRIC_CLIENT_SECRET",
    "FABRIC_TENANT_ID",
    "DATABRICKS_TOKEN",
    "DATABRICKS_CLIENT_ID",
    "DATABRICKS_CLIENT_SECRET",
    "DATABRICKS_GENIE_MCP_URL",
    "DATABRICKS_HOST",
    "DATABRICKS_WORKSPACE_URL",
    "DATABRICKS_GENIE_SPACE_ID",
)


def _clear(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ALL_BACKEND_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _row(rows: list, name: str):
    return next(row for row in rows if row.name == name)


def test_readiness_all_skipped_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear(monkeypatch)

    rows = live_backend_readiness()

    assert {row.name for row in rows} == {"Foundry", "Fabric", "Databricks"}
    assert all(not row.ready for row in rows)
    assert _row(rows, "Fabric").auth == "DefaultAzureCredential"


def test_readiness_fabric_ready_with_endpoint_and_default_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("FABRIC_MCP_URL", "https://fabric.example/mcp")

    fabric = _row(live_backend_readiness(), "Fabric")

    assert fabric.ready is True
    assert fabric.auth == "DefaultAzureCredential"
    assert fabric.hint == "ready"


def test_readiness_fabric_service_principal_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("FABRIC_MCP_URL", "https://fabric.example/mcp")
    monkeypatch.setenv("FABRIC_CLIENT_ID", "client-1")
    monkeypatch.setenv("FABRIC_CLIENT_SECRET", "secret-1")
    monkeypatch.setenv("FABRIC_TENANT_ID", "tenant-1")

    fabric = _row(live_backend_readiness(), "Fabric")

    assert fabric.ready is True
    assert "service-principal" in fabric.auth


def test_readiness_fabric_partial_spn_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("FABRIC_MCP_URL", "https://fabric.example/mcp")
    monkeypatch.setenv("FABRIC_CLIENT_ID", "client-1")

    fabric = _row(live_backend_readiness(), "Fabric")

    assert fabric.ready is False
    assert "FABRIC_CLIENT_SECRET" in fabric.hint


def test_readiness_databricks_ready_with_managed_mcp_oauth(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("DATABRICKS_GENIE_MCP_URL", "https://adb.example/api/2.0/mcp/genie/space")
    monkeypatch.setenv("DATABRICKS_CLIENT_ID", "spn-1")
    monkeypatch.setenv("DATABRICKS_CLIENT_SECRET", "spn-secret")

    databricks = _row(live_backend_readiness(), "Databricks")

    assert databricks.ready is True
    assert databricks.auth == "OAuth M2M"
