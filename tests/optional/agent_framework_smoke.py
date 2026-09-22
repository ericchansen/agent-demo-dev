"""Real optional-runtime construction: pytest tests/optional/agent_framework_smoke.py.

This explicit smoke target requires the agent-framework extra and never skips missing
dependencies. Its filename keeps it out of the default, base-dependency test suite.
Construction checks do not exercise a live model or execute the workflows.
"""

from __future__ import annotations

import socket
from dataclasses import replace
from typing import Any, NoReturn

import pytest
from agent_framework import Workflow

from src.orchestrator.multi_agent.agent_framework_runtime import (
    build_foundry_chat_client,
    build_handoff_workflow,
    build_quota_workflow_spec,
    build_sequential_workflow,
    load_agent_framework_adapters,
)


def _forbid_external_call(*args: Any, **kwargs: Any) -> NoReturn:
    raise AssertionError("Offline workflow construction must not access the network or acquire tokens")


class _OfflineCredential:
    get_token = staticmethod(_forbid_external_call)
    get_token_info = staticmethod(_forbid_external_call)

    def close(self) -> None:
        pass


@pytest.mark.parametrize("data_source", ["fabric", "databricks"])
@pytest.mark.parametrize("workflow_kind", ["sequential", "handoff"])
def test_real_foundry_client_and_workflow_build_offline(
    monkeypatch: pytest.MonkeyPatch, data_source: str, workflow_kind: str
) -> None:
    monkeypatch.setattr(socket, "create_connection", _forbid_external_call)
    monkeypatch.setattr(socket.socket, "connect", _forbid_external_call)
    monkeypatch.setattr(socket.socket, "connect_ex", _forbid_external_call)
    adapters = replace(load_agent_framework_adapters(), credential_factory=_OfflineCredential)
    client = build_foundry_chat_client(
        project_endpoint="https://example.services.ai.azure.com/api/projects/offline-test",
        model="offline-test",
        adapters=adapters,
    )

    builder = {"sequential": build_sequential_workflow, "handoff": build_handoff_workflow}[workflow_kind]
    workflow = builder(client=client, data_source=data_source, adapters=adapters)

    assert isinstance(client, adapters.chat_client_cls)
    assert isinstance(workflow, Workflow)
    expected_agents = {stage.registration.foundry_agent_name for stage in build_quota_workflow_spec(data_source).stages}
    assert expected_agents <= workflow.executors.keys()
    for name in expected_agents:
        assert isinstance(workflow.executors[name].agent, adapters.agent_cls)
