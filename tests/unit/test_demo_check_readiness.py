"""Tests for the live backend readiness matrix in demo_check."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import demo_check
from scripts.demo_check import check_foundry_tools, live_backend_readiness

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


@pytest.mark.parametrize("field,value", [("command", "node"), ("args", ["-m", "missing_server"])])
def test_mcp_readiness_rejects_drifted_entrypoint(
    monkeypatch: pytest.MonkeyPatch, field: str, value: object
) -> None:
    load_json = demo_check._load_json_without_duplicate_keys

    def drifted_config(path: Path):
        payload = load_json(path)
        if path == demo_check.ROOT / "src" / "cli" / "mcp-config.json":
            payload["mcpServers"]["report-generator"][field] = value
        return payload

    monkeypatch.setattr(demo_check, "_load_json_without_duplicate_keys", drifted_config)
    with pytest.raises(ValueError, match="must launch python -m"):
        demo_check.check_mcp_configs()


def test_local_mcp_readiness_rejects_wrong_advertised_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    class WrongToolsClient:
        def __init__(self, transport):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def list_tools(self):
            return SimpleNamespace(tools=[SimpleNamespace(name="unexpected_tool")])

    monkeypatch.setattr("mcp.Client", WrongToolsClient)
    monkeypatch.setattr("mcp.client.stdio.stdio_client", lambda params: object())
    with pytest.raises(ValueError, match="researcher-agent tool discovery mismatch"):
        demo_check.check_local_mcp_servers()


def test_foundry_tool_readiness_uses_fabric_server_labels() -> None:
    assert check_foundry_tools() == "9 tools registered, 7 local handlers"


def test_foundry_tool_readiness_rejects_swapped_fabric_connections(monkeypatch: pytest.MonkeyPatch) -> None:
    from azure.ai.projects.models import FabricIQPreviewTool

    from src.orchestrator import foundry_agent
    from src.orchestrator.config import OrchestratorConfig

    build_tools = foundry_agent._build_tools

    def swapped_tools(config: OrchestratorConfig):
        tools, handlers = build_tools(config)
        for tool in tools:
            if isinstance(tool, FabricIQPreviewTool):
                tool.server_label = (
                    "real_world_market_data" if tool.server_label == "wwi_sales_data" else "wwi_sales_data"
                )
        return tools, handlers

    monkeypatch.setattr(foundry_agent, "_build_tools", swapped_tools)
    with pytest.raises(ValueError, match="labels do not match"):
        check_foundry_tools()


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
