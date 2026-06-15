"""Unit tests for Databricks Supervisor Agent request helpers."""

from __future__ import annotations

import pytest

from src.orchestrator.databricks_supervisor import (
    DatabricksSupervisorClient,
    DatabricksSupervisorConfigurationError,
    SupervisorRequest,
    SupervisorToolSpec,
    build_quota_supervisor_request,
    databricks_supervisor_query_func,
)


def test_genie_space_tool_payload() -> None:
    tool = SupervisorToolSpec.genie_space(name="WWI sales Genie", space_id="space-123")

    assert tool.to_payload() == {
        "type": "genie_space",
        "name": "WWI sales Genie",
        "genie_space": {"space_id": "space-123"},
    }


def test_supervisor_request_payload_from_string_prompt() -> None:
    request = SupervisorRequest(
        model="databricks-claude-sonnet-4-5",
        input="Generate a quota report",
        tools=[SupervisorToolSpec.uc_function(name="quota", function_name="main.sales.generate_quota")],
    )

    payload = request.to_payload()

    assert payload["model"] == "databricks-claude-sonnet-4-5"
    assert payload["input"] == [{"type": "message", "role": "user", "content": "Generate a quota report"}]
    assert payload["tools"] == [
        {
            "type": "uc_function",
            "name": "quota",
            "uc_function": {"name": "main.sales.generate_quota"},
        }
    ]
    assert payload["stream"] is False


def test_build_quota_supervisor_request_uses_genie_and_quota_tools() -> None:
    request = build_quota_supervisor_request(
        "Generate an aggressive quota report",
        customer_name="Tailspin Toys",
        model="databricks-claude-sonnet-4-5",
        genie_space_id="space-123",
        quota_function_name="main.sales.generate_quota",
    )

    payload = request.to_payload()

    assert "Tailspin Toys" in str(payload["input"])
    assert [tool["type"] for tool in payload["tools"]] == ["genie_space", "uc_function"]


def test_build_quota_supervisor_request_requires_tool() -> None:
    with pytest.raises(DatabricksSupervisorConfigurationError, match="Configure at least one"):
        build_quota_supervisor_request("Generate a quota report")


def test_tool_func_reports_configuration_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABRICKS_SUPERVISOR_GENIE_SPACE_ID", raising=False)
    monkeypatch.delenv("DATABRICKS_SUPERVISOR_QUOTA_FUNCTION", raising=False)

    result = databricks_supervisor_query_func({"question": "Generate a quota report"})

    assert result["status"] == "configuration_error"
    assert "DATABRICKS_SUPERVISOR_GENIE_SPACE_ID" in result["required_environment"][0]


def test_client_passes_payload_to_injected_client() -> None:
    class _Responses:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def create(self, **kwargs: object) -> dict[str, object]:
            self.calls.append(kwargs)
            return {"id": "response-1"}

    class _Client:
        def __init__(self) -> None:
            self.responses = _Responses()

    injected = _Client()
    client = DatabricksSupervisorClient(client=injected)
    request = SupervisorRequest(
        model="model",
        input="question",
        tools=[SupervisorToolSpec.genie_space(name="genie", space_id="space")],
    )

    assert client.query(request) == {"id": "response-1"}
    assert injected.responses.calls[0]["model"] == "model"
