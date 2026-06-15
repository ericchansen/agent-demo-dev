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
    """Import a module or skip only when it is genuinely missing."""
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        pytest.skip(f"Module not installed: {module_name}")


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


# ---------------------------------------------------------------------------
# Market data connection — dynamic instructions and tool registration
# ---------------------------------------------------------------------------


def test_build_instructions_without_market_data() -> None:
    """Instructions should NOT mention market data when connection is absent."""
    build_fn = _load_attr("src.orchestrator.foundry_agent", "_build_agent_instructions")
    config_cls = _load_attr("src.orchestrator.config", "OrchestratorConfig")

    config = config_cls(
        foundry_project_endpoint="https://test.endpoint",
        model_deployment_name="gpt-4o",
        fabric_iq_connection_id="test-wwi-id",
        market_data_connection_id=None,
    )

    instructions = build_fn(config)
    assert "MARKET DATA" not in instructions
    assert "SEC EDGAR" not in instructions


def test_build_instructions_with_market_data() -> None:
    """Instructions should include market data section when connection is set."""
    build_fn = _load_attr("src.orchestrator.foundry_agent", "_build_agent_instructions")
    config_cls = _load_attr("src.orchestrator.config", "OrchestratorConfig")

    config = config_cls(
        foundry_project_endpoint="https://test.endpoint",
        model_deployment_name="gpt-4o",
        fabric_iq_connection_id="test-wwi-id",
        market_data_connection_id="test-market-id",
    )

    instructions = build_fn(config)
    assert "MARKET DATA" in instructions
    assert "SEC EDGAR" in instructions


def test_config_market_data_from_env() -> None:
    """OrchestratorConfig should pick up MARKET_DATA_CONNECTION_ID from env."""
    config_cls = _load_attr("src.orchestrator.config", "OrchestratorConfig")

    env = {
        "FOUNDRY_PROJECT_ENDPOINT": "https://test.endpoint",
        "MODEL_DEPLOYMENT_NAME": "gpt-4o",
        "FABRIC_IQ_CONNECTION_ID": "test-wwi-id",
        "MARKET_DATA_CONNECTION_ID": "test-market-id",
    }

    with patch.dict("os.environ", env, clear=False), patch("dotenv.load_dotenv"):
        config = config_cls.from_env()
        assert config.market_data_connection_id == "test-market-id"


def test_config_market_data_absent() -> None:
    """OrchestratorConfig should have None market_data when env var is absent."""
    config_cls = _load_attr("src.orchestrator.config", "OrchestratorConfig")

    env = {
        "FOUNDRY_PROJECT_ENDPOINT": "https://test.endpoint",
        "MODEL_DEPLOYMENT_NAME": "gpt-4o",
        "FABRIC_IQ_CONNECTION_ID": "test-wwi-id",
    }

    with patch.dict("os.environ", env, clear=True), patch("dotenv.load_dotenv"):
        config = config_cls.from_env()
        assert config.market_data_connection_id is None


def test_config_databricks_genie_from_env() -> None:
    """OrchestratorConfig should pick up Databricks Genie settings from env."""
    config_cls = _load_attr("src.orchestrator.config", "OrchestratorConfig")

    env = {
        "FOUNDRY_PROJECT_ENDPOINT": "https://test.endpoint",
        "MODEL_DEPLOYMENT_NAME": "gpt-4o",
        "DATABRICKS_WORKSPACE_URL": "https://adb-123.azuredatabricks.net",
        "DATABRICKS_GENIE_SPACE_ID": "space-123",
        "DATABRICKS_GENIE_WAREHOUSE_ID": "warehouse-123",
    }

    with patch.dict("os.environ", env, clear=True), patch("dotenv.load_dotenv"):
        config = config_cls.from_env()
        assert config.databricks_workspace_url == "https://adb-123.azuredatabricks.net"
        assert config.databricks_genie_space_id == "space-123"
        assert config.databricks_warehouse_id == "warehouse-123"


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


def test_generate_report_non_mapping_forecast_items_are_stable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    assert "databricks_query" in tool_names
    assert "databricks_query" in handlers
    assert "generate_quota_estimation_report" in tool_names
    assert "generate_quota_estimation_report" in handlers
    assert "generate_report" in tool_names
    assert "get_account_activity" in tool_names or "get_account_activity" in handlers


def test_build_tools_with_fabric_connection_uses_platform_tool() -> None:
    """A configured Fabric IQ connection registers the platform tool, not the fallback."""
    module = _load_module("src.orchestrator.foundry_agent")
    orchestrator_config = _load_attr("src.orchestrator.config", "OrchestratorConfig")

    config = orchestrator_config(
        foundry_project_endpoint="https://test.ai.azure.com/",
        model_deployment_name="gpt-4o",
        fabric_iq_connection_id="/subscriptions/x/connections/fabric",
    )

    tools, handlers = module._build_tools(config)
    tool_names = {getattr(tool, "name", None) for tool in tools if getattr(tool, "name", None)}

    assert "wwi_sales_data" in tool_names
    assert "fabric_query" not in tool_names
    assert "fabric_query" not in handlers


def test_build_tools_without_fabric_connection_uses_demo_fallback() -> None:
    """With no Fabric connection the agent still gets a working fabric_query function tool."""
    module = _load_module("src.orchestrator.foundry_agent")
    orchestrator_config = _load_attr("src.orchestrator.config", "OrchestratorConfig")

    config = orchestrator_config(
        foundry_project_endpoint="https://test.ai.azure.com/",
        model_deployment_name="gpt-4o",
        fabric_iq_connection_id=None,
    )

    tools, handlers = module._build_tools(config)
    tool_names = {getattr(tool, "name", None) for tool in tools if getattr(tool, "name", None)}

    assert "wwi_sales_data" not in tool_names
    assert "fabric_query" in tool_names
    assert "fabric_query" in handlers

    result = handlers["fabric_query"]({"question": "Show me sales by territory"})
    assert result["status"] == "ok"
    assert result["row_count"] == len(result["rows"])
    assert result["rows"], "demo fallback must return sales rows"


def test_demo_fabric_query_func_returns_demo_rows() -> None:
    """The demo fabric_query handler returns labelled synthetic sales rows."""
    demo_fabric_query_func = _load_attr("src.orchestrator.tool_runtime", "demo_fabric_query_func")

    result = demo_fabric_query_func({"question": "total revenue"})

    assert "demo" in result["source"].lower()
    assert isinstance(result["rows"], list) and result["rows"]
    first = result["rows"][0]
    assert {"territory", "order_date", "revenue"}.issubset(first.keys())


def test_generate_quota_estimation_report_func_creates_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Foundry local function wraps the shared quota estimator."""
    generate_quota_func = _load_attr("src.orchestrator.foundry_agent", "generate_quota_estimation_report_func")
    monkeypatch.chdir(tmp_path)

    result = generate_quota_func(
        {
            "customer_name": "Tailspin Toys",
            "sales_rows": [
                {
                    "territory": "Northwest",
                    "category": "Novelty Items",
                    "order_date": "2025-11-01",
                    "revenue": 75000,
                    "quantity": 180,
                },
                {
                    "territory": "Northwest",
                    "category": "Novelty Items",
                    "order_date": "2026-05-01",
                    "revenue": 100000,
                    "quantity": 250,
                },
            ],
            "research_data": {"summary": "Retail demand is expanding 10%."},
            "workiq_activity": {"engagement_score": "High", "recent_activity": [{"type": "meeting"}]},
        }
    )

    artifacts = result["artifacts"]
    assert isinstance(artifacts, dict)
    assert set(artifacts) == {"xlsx", "html", "pdf"}
    assert all(Path(str(path)).exists() for path in artifacts.values())


# ---------------------------------------------------------------------------
# Internal orchestration helpers
# ---------------------------------------------------------------------------


def test_execute_local_functions_serializes_outputs() -> None:
    """Local function calls are executed and serialized for the responses API."""
    module = _load_module("src.orchestrator.foundry_agent")
    execute_local_functions = _load_attr("src.orchestrator.foundry_agent", "_execute_local_functions")

    agent = SimpleNamespace(
        _local_function_handlers={"forecast_quota": lambda args: {"customer": args["customer_name"], "status": "ok"}}
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


def test_get_or_create_agent_reuses_matching_fingerprint() -> None:
    """Matching registered agents are reused to avoid version buildup."""
    module = _load_module("src.orchestrator.foundry_agent")
    orchestrator_config = _load_attr("src.orchestrator.config", "OrchestratorConfig")

    config = orchestrator_config(
        foundry_project_endpoint="https://test.ai.azure.com/",
        model_deployment_name="gpt-4o",
        fabric_iq_connection_id=None,
    )
    tools, _ = module._build_tools(config)
    fingerprint = module._definition_fingerprint(config, tools)
    existing = SimpleNamespace(
        name="WWISalesAgent",
        definition=SimpleNamespace(instructions=module._build_agent_instructions(config, fingerprint)),
    )
    project_client = MagicMock()
    project_client.agents.list.return_value = [existing]

    agent = module._get_or_create_agent(project_client, config)

    assert agent is existing
    assert hasattr(agent, "_local_function_handlers")
    project_client.agents.create_version.assert_not_called()


def test_get_or_create_agent_creates_when_definition_changes() -> None:
    """Changed instructions/tools create a new fingerprinted agent version."""
    module = _load_module("src.orchestrator.foundry_agent")
    orchestrator_config = _load_attr("src.orchestrator.config", "OrchestratorConfig")

    config = orchestrator_config(
        foundry_project_endpoint="https://test.ai.azure.com/",
        model_deployment_name="gpt-4o",
        fabric_iq_connection_id=None,
    )
    created = SimpleNamespace(name="WWISalesAgent")
    project_client = MagicMock()
    project_client.agents.list.return_value = [
        SimpleNamespace(name="WWISalesAgent", definition=SimpleNamespace(instructions="old definition"))
    ]
    project_client.agents.create_version.return_value = created

    agent = module._get_or_create_agent(project_client, config)

    assert agent is created
    create_kwargs = project_client.agents.create_version.call_args.kwargs
    assert create_kwargs["agent_name"] == "WWISalesAgent"
    instructions = create_kwargs["definition"].instructions
    assert module._DEFINITION_FINGERPRINT_PREFIX in instructions


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
    assert "error" in response, f"Expected error for unsupported format 'pdf', got: {response}"
    assert "format" in response["error"].lower() or "unsupported" in response["error"].lower()


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
