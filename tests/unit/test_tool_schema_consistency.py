"""Drift guards keeping every agent surface on a single tool-schema source.

The Foundry orchestrator, the hosted-container runtime, and the local
dependency-light runtime all advertise the same function tools. These tests
fail loudly if any surface re-defines a schema or stops exposing a canonical
tool, which previously caused silent contract drift between the Copilot CLI
prototype and the Foundry-hosted production agent.
"""

from __future__ import annotations

from src.orchestrator import foundry_agent, hosted_agent, tool_runtime, tool_schemas

_SHARED_SCHEMA_NAMES = (
    "ACCOUNT_ACTIVITY_SCHEMA",
    "COMPUTE_ATTAINMENT_SCHEMA",
    "DATABRICKS_QUERY_SCHEMA",
    "FORECAST_QUOTA_SCHEMA",
    "GENERATE_QUOTA_ESTIMATION_REPORT_SCHEMA",
    "GENERATE_REPORT_SCHEMA",
    "WEB_RESEARCH_SCHEMA",
)


def test_foundry_and_runtime_reuse_shared_schema_objects() -> None:
    for name in _SHARED_SCHEMA_NAMES:
        canonical = getattr(tool_schemas, name)
        assert getattr(foundry_agent, name) is canonical, f"foundry_agent redefined {name}"
        assert getattr(tool_runtime, name) is canonical, f"tool_runtime redefined {name}"


def test_hosted_runtime_advertises_canonical_tool_names() -> None:
    hosted_names = {tool["function"]["name"] for tool in hosted_agent.TOOLS}
    assert hosted_names == set(tool_schemas.TOOL_NAMES)
    assert set(hosted_agent.TOOL_HANDLERS) == set(tool_schemas.TOOL_NAMES)


def test_hosted_tool_schemas_match_shared_source() -> None:
    schema_by_tool = {tool["function"]["name"]: tool["function"]["parameters"] for tool in hosted_agent.TOOLS}
    assert schema_by_tool["forecast_quota"] is tool_schemas.FORECAST_QUOTA_SCHEMA
    assert schema_by_tool["databricks_query"] is tool_schemas.DATABRICKS_QUERY_SCHEMA
    assert schema_by_tool["generate_quota_estimation_report"] is tool_schemas.GENERATE_QUOTA_ESTIMATION_REPORT_SCHEMA
    assert schema_by_tool["generate_report"] is tool_schemas.GENERATE_REPORT_SCHEMA
    assert schema_by_tool["web_research"] is tool_schemas.WEB_RESEARCH_SCHEMA
    assert schema_by_tool["compute_quota_attainment"] is tool_schemas.COMPUTE_ATTAINMENT_SCHEMA
    assert schema_by_tool["get_account_activity"] is tool_schemas.ACCOUNT_ACTIVITY_SCHEMA


def test_canonical_tool_names_are_stable() -> None:
    assert tool_schemas.TOOL_NAMES == frozenset(
        {
            "fabric_query",
            "databricks_query",
            "forecast_quota",
            "generate_quota_estimation_report",
            "generate_report",
            "web_research",
            "compute_quota_attainment",
            "get_account_activity",
        }
    )
