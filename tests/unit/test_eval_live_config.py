"""Tests for live Fabric eval configuration gates."""

from __future__ import annotations

import pytest

from tests.eval.run_eval import LiveEvalConfigurationError, validate_live_eval_config


def test_live_eval_config_blocks_when_endpoint_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FABRIC_MCP_URL", raising=False)
    monkeypatch.delenv("FABRIC_WORKSPACE_ID", raising=False)
    monkeypatch.delenv("FABRIC_DATA_AGENT_ID", raising=False)

    with pytest.raises(LiveEvalConfigurationError, match="Live Fabric eval is blocked"):
        validate_live_eval_config()


def test_live_eval_config_accepts_explicit_mcp_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "FABRIC_MCP_URL", "https://api.fabric.microsoft.com/v1/mcp/workspaces/workspace/dataagents/agent/agent"
    )
    monkeypatch.delenv("FABRIC_WORKSPACE_ID", raising=False)
    monkeypatch.delenv("FABRIC_DATA_AGENT_ID", raising=False)

    validate_live_eval_config()


def test_live_eval_config_accepts_workspace_and_agent_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FABRIC_MCP_URL", raising=False)
    monkeypatch.setenv("FABRIC_WORKSPACE_ID", "workspace")
    monkeypatch.setenv("FABRIC_DATA_AGENT_ID", "agent")

    validate_live_eval_config()
