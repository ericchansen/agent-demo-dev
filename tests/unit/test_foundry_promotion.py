"""Offline tests for the Foundry multi-agent promotion path.

These tests validate that the promotion helpers construct real, shipping
``azure.ai.projects.models`` objects (the new Responses API path) without making any live
Foundry calls. They are the executable proof that the documented promotion path matches the
SDK that is actually installed.
"""

from __future__ import annotations

from typing import Any

import pytest
from azure.ai.projects.models import PromptAgentDefinition, WorkflowAgentDefinition

from src.orchestrator.multi_agent.foundry_promotion import (
    A2A_SUB_AGENT_SLOTS,
    build_a2a_orchestrator_definition,
    build_workflow_agent_definition,
    register_multi_agent_orchestrator,
)


def test_build_a2a_orchestrator_definition_has_one_tool_per_sub_agent() -> None:
    connection_ids = {slot: f"conn-{slot}" for slot in A2A_SUB_AGENT_SLOTS}

    definition = build_a2a_orchestrator_definition(model="gpt-4o", sub_agent_connection_ids=connection_ids)

    assert isinstance(definition, PromptAgentDefinition)
    assert definition.kind == "prompt"
    assert len(definition.tools) == len(A2A_SUB_AGENT_SLOTS)
    tool_dicts = [tool.as_dict() for tool in definition.tools]
    assert {tool["type"] for tool in tool_dicts} == {"a2a_preview"}
    assert {tool["name"] for tool in tool_dicts} == set(A2A_SUB_AGENT_SLOTS)
    assert {tool["project_connection_id"] for tool in tool_dicts} == set(connection_ids.values())


def test_build_a2a_orchestrator_definition_rejects_empty_inputs() -> None:
    with pytest.raises(ValueError):
        build_a2a_orchestrator_definition(model="", sub_agent_connection_ids={"fsa-data": "c1"})
    with pytest.raises(ValueError):
        build_a2a_orchestrator_definition(model="gpt-4o", sub_agent_connection_ids={})
    with pytest.raises(ValueError):
        build_a2a_orchestrator_definition(model="gpt-4o", sub_agent_connection_ids={"fsa-data": ""})


def test_build_workflow_agent_definition_wraps_yaml() -> None:
    workflow_yaml = "kind: workflow\nname: quota-pipeline\n"

    definition = build_workflow_agent_definition(workflow_yaml)

    assert isinstance(definition, WorkflowAgentDefinition)
    assert definition.kind == "workflow"
    assert definition.workflow == workflow_yaml


def test_build_workflow_agent_definition_rejects_empty_yaml() -> None:
    with pytest.raises(ValueError):
        build_workflow_agent_definition("   ")


def test_register_multi_agent_orchestrator_calls_create_version() -> None:
    calls: dict[str, Any] = {}

    class _FakeAgents:
        def create_version(self, *, agent_name: str, definition: Any) -> str:
            calls["agent_name"] = agent_name
            calls["definition"] = definition
            return "agent-version-1"

    class _FakeProjectClient:
        agents = _FakeAgents()

    definition = build_a2a_orchestrator_definition(
        model="gpt-4o",
        sub_agent_connection_ids={slot: f"conn-{slot}" for slot in A2A_SUB_AGENT_SLOTS},
    )

    result = register_multi_agent_orchestrator(
        _FakeProjectClient(),
        agent_name="WWIMultiAgentOrchestrator",
        definition=definition,
    )

    assert result == "agent-version-1"
    assert calls["agent_name"] == "WWIMultiAgentOrchestrator"
    assert calls["definition"] is definition
