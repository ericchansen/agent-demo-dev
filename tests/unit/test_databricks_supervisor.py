"""Unit tests for Databricks Supervisor Agent request helpers."""

from __future__ import annotations

import pytest

from src.orchestrator.databricks_supervisor import (
    DatabricksSupervisorClient,
    DatabricksSupervisorConfigurationError,
    SupervisorRequest,
    SupervisorToolSpec,
    SupervisorTraceDestination,
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


def test_dashboard_tool_payload_includes_description() -> None:
    tool = SupervisorToolSpec.dashboard(
        name="Sales dashboard",
        dashboard_id="dash-9",
        description="Grounds answers in the published dashboard.",
    )

    assert tool.to_payload() == {
        "type": "dashboard",
        "name": "Sales dashboard",
        "dashboard": {"dashboard_id": "dash-9"},
        "description": "Grounds answers in the published dashboard.",
    }


def test_knowledge_assistant_tool_payload() -> None:
    tool = SupervisorToolSpec.knowledge_assistant(name="Docs", knowledge_assistant_id="ka-1")

    assert tool.to_payload() == {
        "type": "knowledge_assistant",
        "name": "Docs",
        "knowledge_assistant": {"knowledge_assistant_id": "ka-1"},
    }


def test_serving_endpoint_tool_payload() -> None:
    tool = SupervisorToolSpec.serving_endpoint(name="Custom agent", endpoint_name="quota-agent")

    assert tool.to_payload() == {
        "type": "serving_endpoint",
        "name": "Custom agent",
        "serving_endpoint": {"name": "quota-agent"},
    }


def test_tool_specs_require_nonempty_config() -> None:
    with pytest.raises(ValueError, match="dashboard_id"):
        SupervisorToolSpec.dashboard(name="d", dashboard_id="  ")
    with pytest.raises(ValueError, match="knowledge_assistant_id"):
        SupervisorToolSpec.knowledge_assistant(name="k", knowledge_assistant_id="")
    with pytest.raises(ValueError, match="endpoint_name"):
        SupervisorToolSpec.serving_endpoint(name="s", endpoint_name="")


def test_trace_destination_payload() -> None:
    dest = SupervisorTraceDestination(catalog_name="main", schema_name="sales", table_prefix="supervisor_traces")

    assert dest.to_payload() == {
        "catalog_name": "main",
        "schema_name": "sales",
        "table_prefix": "supervisor_traces",
    }


def test_trace_destination_requires_all_fields() -> None:
    with pytest.raises(ValueError, match="schema_name"):
        SupervisorTraceDestination(catalog_name="main", schema_name="", table_prefix="t").to_payload()


def test_request_payload_includes_trace_destination_extra_body() -> None:
    request = SupervisorRequest(
        model="databricks-claude-sonnet-4-5",
        input="Generate a quota report",
        tools=[SupervisorToolSpec.uc_function(name="quota", function_name="main.sales.generate_quota")],
        trace_destination=SupervisorTraceDestination("main", "sales", "supervisor_traces"),
    )

    payload = request.to_payload()

    assert payload["extra_body"] == {
        "trace_destination": {
            "catalog_name": "main",
            "schema_name": "sales",
            "table_prefix": "supervisor_traces",
        }
    }


def test_request_payload_omits_extra_body_without_trace_destination() -> None:
    request = SupervisorRequest(
        model="databricks-claude-sonnet-4-5",
        input="Generate a quota report",
        tools=[SupervisorToolSpec.uc_function(name="quota", function_name="main.sales.generate_quota")],
    )

    assert "extra_body" not in request.to_payload()


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


def test_build_quota_supervisor_request_wires_all_tool_types_and_trace() -> None:
    request = build_quota_supervisor_request(
        "Generate a quota report",
        genie_space_id="space-1",
        quota_function_name="main.sales.generate_quota",
        dashboard_id="dash-1",
        knowledge_assistant_id="ka-1",
        serving_endpoint_name="quota-agent",
        trace_destination=SupervisorTraceDestination("main", "sales", "supervisor_traces"),
    )

    payload = request.to_payload()

    assert [tool["type"] for tool in payload["tools"]] == [
        "genie_space",
        "uc_function",
        "dashboard",
        "knowledge_assistant",
        "serving_endpoint",
    ]
    assert payload["extra_body"] == {
        "trace_destination": {
            "catalog_name": "main",
            "schema_name": "sales",
            "table_prefix": "supervisor_traces",
        }
    }


def test_tool_func_wires_trace_destination_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABRICKS_SUPERVISOR_GENIE_SPACE_ID", "space-1")
    monkeypatch.setenv("DATABRICKS_SUPERVISOR_TRACE_CATALOG", "main")
    monkeypatch.setenv("DATABRICKS_SUPERVISOR_TRACE_SCHEMA", "sales")
    monkeypatch.setenv("DATABRICKS_SUPERVISOR_TRACE_TABLE_PREFIX", "supervisor_traces")

    class _Responses:
        def create(self, **kwargs: object) -> dict[str, object]:
            return {"id": "response-1", "received": kwargs}

    class _Client:
        def __init__(self) -> None:
            self.responses = _Responses()

    import src.orchestrator.databricks_supervisor as mod

    original_client_cls = mod.DatabricksSupervisorClient
    monkeypatch.setattr(mod, "DatabricksSupervisorClient", lambda: original_client_cls(client=_Client()))

    result = databricks_supervisor_query_func({"question": "Generate a quota report"})

    assert result["status"] == "ok"
    assert result["request"]["extra_body"]["trace_destination"]["catalog_name"] == "main"


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
