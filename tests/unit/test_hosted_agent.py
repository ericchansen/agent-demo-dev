"""Unit tests for the Azure AI Foundry hosted-agent runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.orchestrator import hosted_agent


def test_hosted_agent_exposes_all_demo_tools() -> None:
    tool_names = {tool["function"]["name"] for tool in hosted_agent.TOOLS}

    assert {
        "fabric_query",
        "forecast_quota",
        "generate_quota_estimation_report",
        "generate_report",
        "web_research",
        "compute_quota_attainment",
        "get_account_activity",
    } <= tool_names
    assert set(hosted_agent.TOOL_HANDLERS) == tool_names


def test_fabric_query_returns_clear_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FABRIC_MCP_URL", raising=False)
    monkeypatch.delenv("FABRIC_MCP_TOOL_NAME", raising=False)

    result = hosted_agent.handle_fabric_query({"question": "Top customers by revenue"})

    assert result["status"] == "configuration_error"
    assert "FABRIC_MCP_URL" in result["message"]
    assert result["required_environment"] == ["FABRIC_MCP_URL", "FABRIC_MCP_TOOL_NAME"]


def test_process_invocation_generates_quota_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOSTED_AGENT_OUTPUT_DIR", str(tmp_path))

    response = hosted_agent.process_invocation("Generate a quota report for Tailspin Toys")

    assert "Generated a quota estimation report for Tailspin Toys" in response
    assert (tmp_path / "tailspin_toys_base_quota_estimate.xlsx").exists()
    assert (tmp_path / "tailspin_toys_base_quota_estimate.html").exists()
    assert (tmp_path / "tailspin_toys_base_quota_estimate.pdf").exists()


def test_process_invocation_executes_injected_adapter_tool_call() -> None:
    class Adapter:
        def __init__(self) -> None:
            self.calls = 0
            self.messages: list[list[dict[str, Any]]] = []

        def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
            self.calls += 1
            self.messages.append(messages)
            assert any(tool["function"]["name"] == "forecast_quota" for tool in tools)
            if self.calls == 1:
                return {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "function": {
                                "name": "forecast_quota",
                                "arguments": json.dumps({"customer_name": "Tailspin Toys"}),
                            },
                        }
                    ],
                }
            tool_content = messages[-1]["content"]
            assert messages[-1]["role"] == "tool"
            assert "Tailspin Toys" in tool_content
            return {"content": "Forecast complete.", "tool_calls": []}

    adapter = Adapter()

    response = hosted_agent.process_invocation("Forecast quota for Tailspin Toys", adapter=adapter)

    assert response == "Forecast complete."
    assert adapter.calls == 2


def test_execute_tool_rejects_unknown_tool() -> None:
    with pytest.raises(ValueError, match="Unknown hosted agent tool"):
        hosted_agent.execute_tool("missing_tool", {})
