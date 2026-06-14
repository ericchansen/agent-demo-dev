"""Unit tests for MCP config validity."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_MCP_CONFIG_PATH = Path(__file__).resolve().parents[2] / "src" / "cli" / "mcp-config.json"


@pytest.fixture
def mcp_config() -> dict:
    """Load and parse the MCP config JSON."""
    assert _MCP_CONFIG_PATH.exists(), f"MCP config not found: {_MCP_CONFIG_PATH}"
    with open(_MCP_CONFIG_PATH) as f:
        return json.load(f)


class TestMCPConfigStructure:
    """Validate the MCP server config file structure."""

    def test_has_mcp_servers_key(self, mcp_config):
        """Config must have a top-level 'mcpServers' key."""
        assert "mcpServers" in mcp_config

    def test_wwi_sales_data_present(self, mcp_config):
        """Original WWI sales data server must be present."""
        servers = mcp_config["mcpServers"]
        assert "wwi-sales-data" in servers
        assert servers["wwi-sales-data"]["type"] == "http"

    def test_market_data_present(self, mcp_config):
        """Market data server must be present."""
        servers = mcp_config["mcpServers"]
        assert "market-data" in servers
        assert servers["market-data"]["type"] == "http"

    def test_researcher_agent_present(self, mcp_config):
        """Researcher agent must be present."""
        servers = mcp_config["mcpServers"]
        assert "researcher-agent" in servers
        assert servers["researcher-agent"]["type"] == "stdio"

    def test_all_servers_have_description(self, mcp_config):
        """Every server should have a description."""
        for name, server in mcp_config["mcpServers"].items():
            assert "description" in server, f"Server '{name}' missing description"
            assert len(server["description"]) > 10, f"Server '{name}' description too short"

    def test_http_servers_have_url(self, mcp_config):
        """HTTP-type servers should have a url field."""
        for name, server in mcp_config["mcpServers"].items():
            if server.get("type") == "http":
                assert "url" in server, f"HTTP server '{name}' missing url"

    def test_stdio_servers_have_command(self, mcp_config):
        """Stdio-type servers should have a command field."""
        for name, server in mcp_config["mcpServers"].items():
            if server.get("type") == "stdio":
                assert "command" in server, f"Stdio server '{name}' missing command"

    def test_no_duplicate_descriptions(self, mcp_config):
        """Server descriptions should be unique to avoid routing confusion."""
        descriptions = [s["description"] for s in mcp_config["mcpServers"].values()]
        assert len(descriptions) == len(set(descriptions)), "Duplicate server descriptions found"
