"""Unit tests for MCP config validity."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MCP_CONFIG_PATHS = [
    _ROOT / ".github" / "mcp.json",
    _ROOT / ".vscode" / "mcp.json",
    _ROOT / "src" / "cli" / "mcp-config.json",
]
_EXPECTED_SERVERS = {
    "fabric-core",
    "sales-data",
    "market-data",
    "researcher-agent",
    "sharepoint-agent",
    "report-generator",
    "quota-estimator",
}


@pytest.fixture(params=_MCP_CONFIG_PATHS, ids=lambda path: str(path.relative_to(_ROOT)))
def mcp_config(request: pytest.FixtureRequest) -> tuple[Path, dict[str, Any]]:
    """Load and parse one MCP config JSON file."""
    path = request.param
    assert isinstance(path, Path)
    assert path.exists(), f"MCP config not found: {path}"
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, dict)
    return path, payload


def test_all_mcp_configs_have_expected_servers(mcp_config: tuple[Path, dict[str, Any]]) -> None:
    """Every published MCP config should expose the full demo server set."""
    path, payload = mcp_config

    assert "mcpServers" in payload, f"{path} missing mcpServers"
    servers = payload["mcpServers"]
    assert isinstance(servers, dict)
    assert set(servers) == _EXPECTED_SERVERS


def test_all_mcp_servers_have_descriptions(mcp_config: tuple[Path, dict[str, Any]]) -> None:
    """Every server should have a useful description for tool routing."""
    path, payload = mcp_config

    for name, server in payload["mcpServers"].items():
        assert "description" in server, f"{path}:{name} missing description"
        assert len(server["description"]) > 10, f"{path}:{name} description too short"


def test_mcp_server_transport_fields_are_valid(mcp_config: tuple[Path, dict[str, Any]]) -> None:
    """HTTP servers need URLs and stdio servers need commands."""
    path, payload = mcp_config

    for name, server in payload["mcpServers"].items():
        server_type = server.get("type")
        assert server_type in {"http", "stdio"}, f"{path}:{name} has unsupported type {server_type}"
        if server_type == "http":
            assert isinstance(server.get("url"), str), f"{path}:{name} HTTP server missing url"
        if server_type == "stdio":
            assert isinstance(server.get("command"), str), f"{path}:{name} stdio server missing command"


def test_mcp_config_server_sets_match_across_surfaces() -> None:
    """The GitHub, VS Code, and CLI surfaces should not drift."""
    server_sets = []
    for path in _MCP_CONFIG_PATHS:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        server_sets.append(set(payload["mcpServers"]))

    assert all(server_set == server_sets[0] for server_set in server_sets)
