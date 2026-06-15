"""Offline tests for the optional Microsoft Agent Framework runtime."""

from __future__ import annotations

from typing import Any

import pytest

from src.orchestrator.multi_agent.agent_framework_runtime import (
    AgentFrameworkAdapters,
    AgentFrameworkConfigurationError,
    build_foundry_chat_client,
    build_handoff_workflow,
    build_quota_workflow_spec,
    build_sequential_workflow,
    resolve_multi_agent_runtime,
    run_agent_framework_pipeline_async,
)


class _FakeCredential:
    pass


class _FakeFoundryChatClient:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class _FakeAgent:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.name = kwargs["name"]


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeAgentResponse:
    def __init__(self, text: str) -> None:
        self.messages = [_FakeMessage(text)]


class _FakeSequentialResult:
    def get_outputs(self) -> list[_FakeAgentResponse]:
        return [_FakeAgentResponse("planner -> data"), _FakeAgentResponse("report artifact plan")]


class _FakeSequentialWorkflow:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def run(self, prompt: str) -> _FakeSequentialResult:
        self.prompts.append(prompt)
        return _FakeSequentialResult()


class _FakeSequentialBuilder:
    calls: list[dict[str, Any]] = []
    workflow = _FakeSequentialWorkflow()

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.calls.append(kwargs)

    def build(self) -> _FakeSequentialWorkflow:
        return self.workflow


class _FakeHandoffBuilder:
    calls: list[dict[str, Any]] = []
    handoffs: list[tuple[str, list[str]]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.calls.append(kwargs)

    def with_start_agent(self, agent: _FakeAgent) -> _FakeHandoffBuilder:
        self.start_agent = agent
        return self

    def add_handoff(self, source: _FakeAgent, targets: list[_FakeAgent]) -> _FakeHandoffBuilder:
        self.handoffs.append((source.name, [target.name for target in targets]))
        return self

    def build(self) -> dict[str, Any]:
        return {"name": self.kwargs["name"], "start": self.start_agent.name, "handoffs": list(self.handoffs)}


def _adapters() -> AgentFrameworkAdapters:
    _FakeSequentialBuilder.calls = []
    _FakeSequentialBuilder.workflow = _FakeSequentialWorkflow()
    _FakeHandoffBuilder.calls = []
    _FakeHandoffBuilder.handoffs = []
    return AgentFrameworkAdapters(
        agent_cls=_FakeAgent,
        chat_client_cls=_FakeFoundryChatClient,
        sequential_builder_cls=_FakeSequentialBuilder,
        handoff_builder_cls=_FakeHandoffBuilder,
        credential_factory=_FakeCredential,
    )


def test_build_quota_workflow_spec_includes_sequential_and_handoff_shape() -> None:
    spec = build_quota_workflow_spec("databricks")

    assert [stage.registration.name for stage in spec.stages] == [
        "planner",
        "data",
        "research",
        "work-context",
        "conversational",
        "report",
    ]
    assert "Databricks Genie" in spec.stages[1].instructions
    assert spec.handoffs[0].source == "planner"
    assert spec.handoffs[-1].targets == ("report",)


def test_build_foundry_chat_client_uses_repo_env_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOUNDRY_PROJECT_ENDPOINT", "https://foundry.example")
    monkeypatch.setenv("MODEL_DEPLOYMENT_NAME", "gpt-4o")

    client = build_foundry_chat_client(adapters=_adapters())

    assert client.kwargs["project_endpoint"] == "https://foundry.example"
    assert client.kwargs["model"] == "gpt-4o"
    assert isinstance(client.kwargs["credential"], _FakeCredential)


def test_build_foundry_chat_client_requires_endpoint_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FOUNDRY_PROJECT_ENDPOINT", raising=False)
    monkeypatch.delenv("FOUNDRY_MODEL", raising=False)
    monkeypatch.delenv("MODEL_DEPLOYMENT_NAME", raising=False)

    with pytest.raises(AgentFrameworkConfigurationError):
        build_foundry_chat_client(adapters=_adapters())


def test_build_sequential_workflow_wires_all_participants() -> None:
    workflow = build_sequential_workflow(client=object(), adapters=_adapters())

    assert isinstance(workflow, _FakeSequentialWorkflow)
    call = _FakeSequentialBuilder.calls[0]
    assert call["output_from"] == "all"
    assert [agent.name for agent in call["participants"]] == [
        "fsa-planner",
        "fsa-data",
        "fsa-research",
        "fsa-work-context",
        "fsa-conversation",
        "fsa-report",
    ]


def test_build_handoff_workflow_wires_start_agent_and_transfers() -> None:
    workflow = build_handoff_workflow(client=object(), adapters=_adapters())

    assert workflow["start"] == "fsa-planner"
    assert ("fsa-planner", ["fsa-data", "fsa-research", "fsa-work-context"]) in workflow["handoffs"]
    assert ("fsa-conversation", ["fsa-report"]) in workflow["handoffs"]
    participants = _FakeHandoffBuilder.calls[0]["participants"]
    assert all(agent.kwargs["require_per_service_call_history_persistence"] for agent in participants)


@pytest.mark.asyncio
async def test_run_agent_framework_pipeline_returns_stage_outputs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOUNDRY_PROJECT_ENDPOINT", "https://foundry.example")
    monkeypatch.setenv("FOUNDRY_MODEL", "gpt-4o")

    result = await run_agent_framework_pipeline_async(
        "Generate a quota report for Tailspin Toys",
        customer_name="Tailspin Toys",
        adapters=_adapters(),
    )

    assert result["runtime"] == "agent-framework"
    assert result["orchestration"] == "sequential"
    assert result["stage_outputs"] == ["planner -> data", "report artifact plan"]
    assert "Tailspin Toys" in _FakeSequentialBuilder.workflow.prompts[0]


def test_resolve_multi_agent_runtime_defaults_and_validates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WWI_MULTI_AGENT_RUNTIME", raising=False)
    assert resolve_multi_agent_runtime() == "deterministic"
    monkeypatch.setenv("WWI_MULTI_AGENT_RUNTIME", "agent-framework")
    assert resolve_multi_agent_runtime() == "agent-framework"
    with pytest.raises(ValueError):
        resolve_multi_agent_runtime("unknown")
