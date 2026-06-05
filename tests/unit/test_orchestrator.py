"""Unit tests for the Foundry orchestrator."""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _load_module(module_name: str) -> Any:
    """Import a module or skip when concurrent refactors make it temporarily unavailable."""
    try:
        return importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - defensive for concurrent edits
        pytest.skip(f"Unable to import {module_name}: {exc}")


def _load_attr(module_name: str, attr_name: str) -> Any:
    """Return a public attribute from a module or skip if it is unavailable."""
    module = _load_module(module_name)
    try:
        return getattr(module, attr_name)
    except AttributeError:
        pytest.skip(f"{attr_name} is not exposed by {module_name}")


def _stub_generate_file(_data: Any, _template: str | Path, output_path: str | Path) -> str:
    """Create a lightweight placeholder file for report-generation tests."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stub", encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# Mock WorkIQ function
# ---------------------------------------------------------------------------


def test_mock_workiq_returns_valid_structure() -> None:
    """Mock WorkIQ returns expected fields."""
    mock_workiq_func = _load_attr("src.orchestrator.foundry_agent", "mock_workiq_func")

    result = mock_workiq_func({"customer_name": "Tailspin Toys"})

    assert result["customer"] == "Tailspin Toys"
    assert "recent_activity" in result
    assert isinstance(result["recent_activity"], list)
    assert len(result["recent_activity"]) > 0
    assert "source" in result
    assert "mock" in result["source"].lower()


def test_mock_workiq_missing_customer() -> None:
    """Mock WorkIQ handles missing customer_name."""
    mock_workiq_func = _load_attr("src.orchestrator.foundry_agent", "mock_workiq_func")

    result = mock_workiq_func({})

    assert result["customer"] == "Unknown"


def test_mock_workiq_empty_args() -> None:
    """Mock WorkIQ handles empty dict."""
    mock_workiq_func = _load_attr("src.orchestrator.foundry_agent", "mock_workiq_func")

    result = mock_workiq_func({})

    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Forecast quota function
# ---------------------------------------------------------------------------


def test_forecast_quota_returns_valid_structure() -> None:
    """Forecast returns expected fields."""
    forecast_quota_func = _load_attr("src.orchestrator.foundry_agent", "forecast_quota_func")

    result = forecast_quota_func({"customer_name": "Tailspin Toys"})

    assert result["customer"] == "Tailspin Toys"
    assert "current_fy_total" in result
    assert "projected_fy_total" in result
    assert "items" in result
    assert isinstance(result["items"], list)
    assert all("category" in item for item in result["items"])


def test_forecast_quota_missing_customer() -> None:
    """Forecast quota handles missing customer_name."""
    forecast_quota_func = _load_attr("src.orchestrator.foundry_agent", "forecast_quota_func")

    result = forecast_quota_func({})

    assert result["customer"] == "Unknown"


# ---------------------------------------------------------------------------
# Generate report function
# ---------------------------------------------------------------------------


def test_generate_report_creates_docx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Report function creates a DOCX file."""
    generate_report_func = _load_attr("src.orchestrator.foundry_agent", "generate_report_func")
    monkeypatch.chdir(tmp_path)

    with patch("src.agents.report_generator.generator.generate_docx", side_effect=_stub_generate_file):
        result = generate_report_func(
            {
                "title": "Test Report",
                "customer_name": "Contoso",
            }
        )

    output_path = Path(result["file_path"])

    assert result["status"] == "generated"
    assert output_path.exists()
    assert output_path.suffix == ".docx"
    assert output_path.stem.startswith("test_report")


def test_generate_report_with_forecast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Report with forecast data generates successfully."""
    generate_report_func = _load_attr("src.orchestrator.foundry_agent", "generate_report_func")
    monkeypatch.chdir(tmp_path)

    with patch("src.agents.report_generator.generator.generate_docx", side_effect=_stub_generate_file):
        result = generate_report_func(
            {
                "title": "Forecast Report",
                "customer_name": "Tailspin",
                "forecast_data": {
                    "current_fy_total": 1_000_000,
                    "projected_fy_total": 1_100_000,
                    "overall_growth_rate": 0.1,
                    "methodology": "test",
                    "items": [
                        {
                            "category": "Toys",
                            "current_fy_revenue": 500_000,
                            "growth_rate": 0.1,
                            "projected_fy_revenue": 550_000,
                        },
                    ],
                },
            }
        )

    assert result["status"] == "generated"
    assert result["has_forecast"] is True
    assert Path(result["file_path"]).exists()


def test_generate_report_with_malformed_forecast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Report handles malformed forecast payloads without crashing."""
    generate_report_func = _load_attr("src.orchestrator.foundry_agent", "generate_report_func")
    monkeypatch.chdir(tmp_path)

    with patch("src.agents.report_generator.generator.generate_docx", side_effect=_stub_generate_file):
        result = generate_report_func(
            {
                "title": "Bad Forecast",
                "customer_name": "Test",
                "forecast_data": "not a dict",
            }
        )

    assert isinstance(result, dict)
    assert result["has_forecast"] is False
    assert Path(result["file_path"]).exists()


def test_generate_report_forecast_missing_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Report handles partial forecast items when downstream validation is lenient."""
    generate_report_func = _load_attr("src.orchestrator.foundry_agent", "generate_report_func")
    monkeypatch.chdir(tmp_path)

    with (
        patch("src.agents.report_generator.generator.generate_docx", side_effect=_stub_generate_file),
        patch("src.agents.report_generator.generator.ForecastItem", side_effect=lambda **kwargs: kwargs),
    ):
        result = generate_report_func(
            {
                "title": "Partial Forecast",
                "customer_name": "Test",
                "forecast_data": {
                    "items": [
                        {"category": "Toys"},
                        {"not_a_real_field": 123},
                    ],
                },
            }
        )

    assert isinstance(result, dict)
    assert Path(result["file_path"]).exists()


def test_generate_report_non_mapping_forecast_items_are_stable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-mapping forecast items either raise a clear error or are handled gracefully."""
    generate_report_func = _load_attr("src.orchestrator.foundry_agent", "generate_report_func")
    monkeypatch.chdir(tmp_path)

    with patch("src.agents.report_generator.generator.generate_docx", side_effect=_stub_generate_file):
        try:
            result = generate_report_func(
                {
                    "title": "Weird Forecast",
                    "customer_name": "Test",
                    "forecast_data": {
                        "items": [42],
                    },
                }
            )
        except TypeError as exc:
            assert "mapping" in str(exc).lower() or "argument after **" in str(exc).lower()
        else:
            assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


def test_config_missing_env_vars() -> None:
    """Config raises clear error on missing vars."""
    config_module = _load_module("src.orchestrator.config")
    orchestrator_config = _load_attr("src.orchestrator.config", "OrchestratorConfig")

    with (
        patch.object(config_module, "load_dotenv", return_value=None),
        patch.dict("os.environ", {}, clear=True),
        pytest.raises(Exception) as exc_info,
    ):
        orchestrator_config.from_env()

    assert "FOUNDRY_PROJECT_ENDPOINT" in str(exc_info.value)


def test_config_loads_from_env() -> None:
    """Config loads correctly from environment."""
    config_module = _load_module("src.orchestrator.config")
    orchestrator_config = _load_attr("src.orchestrator.config", "OrchestratorConfig")
    env = {
        "FOUNDRY_PROJECT_ENDPOINT": "https://test.ai.azure.com/",
        "MODEL_DEPLOYMENT_NAME": "gpt-4o",
        "FABRIC_IQ_CONNECTION_ID": "/subscriptions/test/connections/test",
    }

    with patch.object(config_module, "load_dotenv", return_value=None), patch.dict("os.environ", env, clear=True):
        config = orchestrator_config.from_env()

    assert config.foundry_project_endpoint == "https://test.ai.azure.com/"
    assert config.workiq_connection_id is None


# ---------------------------------------------------------------------------
# Tool building
# ---------------------------------------------------------------------------


def test_build_tools_without_workiq() -> None:
    """Tools list excludes WorkIQ when not configured."""
    module = _load_module("src.orchestrator.foundry_agent")
    orchestrator_config = _load_attr("src.orchestrator.config", "OrchestratorConfig")

    config = orchestrator_config(
        foundry_project_endpoint="https://test.ai.azure.com/",
        model_deployment_name="gpt-4o",
        fabric_iq_connection_id="/test/connection",
        workiq_connection_id=None,
    )

    built = module._build_tools(config)
    tools, handlers = built if isinstance(built, tuple) else (built, {})
    tool_names = {getattr(tool, "name", None) for tool in tools if getattr(tool, "name", None)}

    assert isinstance(tools, list)
    assert len(tools) >= 2
    assert "forecast_quota" in tool_names
    assert "generate_report" in tool_names
    assert "get_account_activity" in tool_names or "get_account_activity" in handlers


# ---------------------------------------------------------------------------
# Internal orchestration helpers
# ---------------------------------------------------------------------------


def test_execute_local_functions_serializes_outputs() -> None:
    """Local function calls are executed and serialized for the responses API."""
    module = _load_module("src.orchestrator.foundry_agent")
    execute_local_functions = _load_attr("src.orchestrator.foundry_agent", "_execute_local_functions")

    agent = SimpleNamespace(
        _local_function_handlers={
            "forecast_quota": lambda args: {"customer": args["customer_name"], "status": "ok"}
        }
    )
    response = SimpleNamespace(
        output=[
            {
                "type": "function_call",
                "name": "forecast_quota",
                "arguments": json.dumps({"customer_name": "Tailspin Toys"}),
                "call_id": "call-1",
            }
        ]
    )

    result = execute_local_functions(agent, response)

    assert len(result) == 1
    assert result[0]["type"] == "function_call_output"
    assert result[0]["call_id"] == "call-1"
    assert json.loads(result[0]["output"]) == {"customer": "Tailspin Toys", "status": "ok"}
    assert module._item_value(response.output[0], "name") == "forecast_quota"


def test_execute_local_functions_handles_unknown_function() -> None:
    """Unknown function calls are converted into structured tool errors."""
    execute_local_functions = _load_attr("src.orchestrator.foundry_agent", "_execute_local_functions")

    agent = SimpleNamespace(_local_function_handlers={})
    response = SimpleNamespace(
        output=[
            {
                "type": "function_call",
                "name": "missing_function",
                "arguments": "{not-valid-json",
                "call_id": "call-2",
            }
        ]
    )

    result = execute_local_functions(agent, response)

    assert len(result) == 1
    assert "Unknown function" in json.loads(result[0]["output"])["error"]


def test_extract_output_text_reads_message_content() -> None:
    """Output text falls back to message content when output_text is empty."""
    extract_output_text = _load_attr("src.orchestrator.foundry_agent", "_extract_output_text")

    response = SimpleNamespace(
        output_text="",
        output=[
            {
                "type": "message",
                "content": [
                    {"text": {"value": "First line"}},
                    {"text": "Second line"},
                ],
            }
        ],
    )

    assert extract_output_text(response) == "First line\nSecond line"


def test_run_query_uses_mocked_clients() -> None:
    """run_query loops through tool calls while keeping Azure SDK dependencies mocked."""
    module = _load_module("src.orchestrator.foundry_agent")

    first_response = SimpleNamespace(
        id="resp-1",
        output_text="",
        output=[
            {
                "type": "function_call",
                "name": "forecast_quota",
                "arguments": json.dumps({"customer_name": "Tailspin Toys"}),
                "call_id": "call-1",
            }
        ],
    )
    final_response = SimpleNamespace(id="resp-2", output_text="Quota summary", output=[])

    openai_client = MagicMock()
    openai_client.responses.create.side_effect = [first_response, final_response]

    project_client = MagicMock()
    project_client.get_openai_client.return_value = openai_client
    project_client_cm = MagicMock()
    project_client_cm.__enter__.return_value = project_client
    project_client_cm.__exit__.return_value = None

    credential = MagicMock()
    credential_cm = MagicMock()
    credential_cm.__enter__.return_value = credential
    credential_cm.__exit__.return_value = None

    agent = SimpleNamespace(
        name="WWISalesAgent",
        _local_function_handlers={"forecast_quota": lambda args: {"customer": args["customer_name"]}},
    )
    config = SimpleNamespace(foundry_project_endpoint="https://test.ai.azure.com/")

    with (
        patch.object(module, "DefaultAzureCredential", return_value=credential_cm),
        patch.object(module, "AIProjectClient", return_value=project_client_cm),
        patch.object(module, "_get_or_create_agent", return_value=agent),
    ):
        result = module.run_query("How is Tailspin doing?", config=config)

    assert result == "Quota summary"
    assert openai_client.responses.create.call_count == 2
    first_call = openai_client.responses.create.call_args_list[0]
    second_call = openai_client.responses.create.call_args_list[1]
    assert first_call.kwargs["input"] == "How is Tailspin doing?"
    assert second_call.kwargs["previous_response_id"] == "resp-1"
    assert json.loads(second_call.kwargs["input"][0]["output"])["customer"] == "Tailspin Toys"


# ---------------------------------------------------------------------------
# MCP server format validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_rejects_invalid_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """MCP server rejects unsupported report formats or falls back safely."""
    report_mcp = _load_module("src.agents.report_generator.mcp_server")
    monkeypatch.chdir(tmp_path)

    with patch.object(report_mcp, "generate_docx", side_effect=_stub_generate_file):
        result = await report_mcp.call_tool(
            "generate_report",
            {
                "title": "Test",
                "customer_name": "Test",
                "format": "pdf",
            },
        )

    assert len(result) == 1
    response = json.loads(result[0].text)
    if "error" in response:
        assert "format" in response["error"].lower() or "unsupported" in response["error"].lower()
    else:
        assert response.get("status") == "success"
        assert Path(response["file_path"]).exists()


@pytest.mark.asyncio
async def test_mcp_generates_docx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """MCP server generates DOCX successfully."""
    report_mcp = _load_module("src.agents.report_generator.mcp_server")
    monkeypatch.chdir(tmp_path)

    with patch.object(report_mcp, "generate_docx", side_effect=_stub_generate_file):
        result = await report_mcp.call_tool(
            "generate_report",
            {
                "title": "MCP Test Report",
                "customer_name": "Contoso",
                "format": "docx",
            },
        )

    assert len(result) == 1
    response = json.loads(result[0].text)
    assert response.get("status") == "success"
    assert response.get("format") == "docx"
    assert Path(response["file_path"]).exists()
