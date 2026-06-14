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


@pytest.mark.parametrize(
    ("prompt", "expected_tool"),
    [
        ("Generate a quota estimation report for Tailspin Toys", "generate_quota_estimation_report"),
        ("What is our quota attainment and pipeline coverage?", "compute_quota_attainment"),
        ("Forecast quota for Contoso", "forecast_quota"),
        ("Show recent account activity for Fabrikam", "get_account_activity"),
        ("Find market news about Northwind", "web_research"),
        ("What were total sales revenue by territory?", "fabric_query"),
    ],
)
def test_local_deterministic_adapter_routes_prompt_to_tool(prompt: str, expected_tool: str) -> None:
    adapter = hosted_agent.LocalDeterministicAdapter()
    messages = [
        {"role": "system", "content": hosted_agent.SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    response = adapter.complete(messages, hosted_agent.TOOLS)

    tool_calls = response["tool_calls"]
    assert len(tool_calls) == 1
    assert tool_calls[0]["function"]["name"] == expected_tool
    assert json.loads(tool_calls[0]["function"]["arguments"]) != {} or expected_tool == "fabric_query"


def test_local_deterministic_adapter_runs_full_tool_loop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOSTED_AGENT_OUTPUT_DIR", str(tmp_path))
    adapter = hosted_agent.LocalDeterministicAdapter()

    response = hosted_agent.process_invocation("Generate a quota estimation report for Tailspin Toys", adapter=adapter)

    assert "generate_quota_estimation_report" in response
    assert (tmp_path / "tailspin_toys_base_quota_estimate.xlsx").exists()


def test_local_deterministic_adapter_unmatched_prompt_returns_ready_message() -> None:
    adapter = hosted_agent.LocalDeterministicAdapter()
    messages = [{"role": "user", "content": "hello there"}]

    response = adapter.complete(messages, hosted_agent.TOOLS)

    assert response["tool_calls"] == []
    assert response["content"] == hosted_agent._READY_MESSAGE


def test_build_adapter_local_returns_deterministic_adapter() -> None:
    assert isinstance(hosted_agent.build_adapter("local"), hosted_agent.LocalDeterministicAdapter)


def test_build_adapter_auto_without_azure_env_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MODEL_ENDPOINT", raising=False)
    monkeypatch.delenv("MODEL_DEPLOYMENT", raising=False)

    assert hosted_agent.build_adapter("auto") is None


def test_build_adapter_azure_missing_config_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MODEL_ENDPOINT", raising=False)
    monkeypatch.delenv("MODEL_DEPLOYMENT", raising=False)

    with pytest.raises(hosted_agent.HostedAgentConfigurationError, match="MODEL_ENDPOINT"):
        hosted_agent.build_adapter("azure")


def test_build_adapter_unknown_mode_raises() -> None:
    with pytest.raises(hosted_agent.HostedAgentConfigurationError, match="Unknown HOSTED_AGENT_ADAPTER"):
        hosted_agent.build_adapter("banana")


def test_azure_adapter_translates_model_response_to_tool_calls() -> None:
    class _Function:
        name = "forecast_quota"
        arguments = json.dumps({"customer_name": "Contoso"})

    class _ToolCall:
        id = "call-xyz"
        function = _Function()

    class _Message:
        content = ""
        tool_calls = [_ToolCall()]

    class _Choice:
        message = _Message()

    class _Response:
        choices = [_Choice()]

    class _Completions:
        def __init__(self) -> None:
            self.captured: dict[str, Any] = {}

        def create(self, **kwargs: Any) -> _Response:
            self.captured = kwargs
            return _Response()

    class _Chat:
        def __init__(self) -> None:
            self.completions = _Completions()

    class _Client:
        def __init__(self) -> None:
            self.chat = _Chat()

    client = _Client()
    adapter = hosted_agent.AzureManagedIdentityChatAdapter(
        project_endpoint="https://example.ai.azure.com/",
        model_deployment="gpt-4o",
        client=client,
    )

    result = adapter.complete([{"role": "user", "content": "Forecast quota"}], hosted_agent.TOOLS)

    assert result["tool_calls"][0]["function"]["name"] == "forecast_quota"
    assert client.chat.completions.captured["model"] == "gpt-4o"
    assert client.chat.completions.captured["tool_choice"] == "auto"


def test_execute_tool_logs_success_metadata_without_payload(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("INFO", logger="src.orchestrator.hosted_agent"):
        hosted_agent.execute_tool("compute_quota_attainment", {})

    records = [
        record.getMessage() for record in caplog.records if "tool=compute_quota_attainment" in record.getMessage()
    ]
    assert records
    assert "status=success" in records[0]
    assert "duration_ms=" in records[0]


def test_execute_tool_logs_and_reraises_failure(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING", logger="src.orchestrator.hosted_agent"):
        with pytest.raises(ValueError):
            hosted_agent.execute_tool("generate_quota_estimation_report", {"customer_name": "X"})

    messages = [record.getMessage() for record in caplog.records]
    assert any("status=error" in message and "exception=ValueError" in message for message in messages)
