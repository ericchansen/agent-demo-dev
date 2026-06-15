"""Implementation path: promoting the local multi-agent PoC to real Foundry APIs.

This module is the verified bridge between the deterministic in-process pipeline in
``pipeline.py`` and the multi-agent primitives that actually ship in this repo's Azure AI
Foundry SDK (``azure-ai-projects>=2.2.0`` — the new Responses API path).

It exists so the promotion path is **import-validated and unit-tested offline** against
real, shipping SDK types, instead of being described in prose that may drift from the API.
The functions construct genuine ``azure.ai.projects.models`` objects but deliberately do
**not** make live Foundry calls: registering A2A connections or workflows requires Foundry
portal setup that cannot be performed from code alone (see citations below). Wire these into
a live project once those connections / workflows exist.

API landscape (verified 2026):

* ``ConnectedAgentTool`` (``azure.ai.agents.models``) is the **classic** threads/runs API and
  is **not** compatible with this repo's ``PromptAgentDefinition`` + Responses API path. Agents
  created with the classic ``create_agent()`` cannot be referenced from ``create_version()``
  prompt agents. Do not use it here.
  https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/migrate
* ``A2APreviewTool`` (``azure.ai.projects.models``, Public Preview) lets one prompt agent call
  another agent exposed as an A2A endpoint. Each sub-agent needs an A2A connection created in
  the Foundry portal; attach one ``A2APreviewTool`` per sub-agent on the orchestrator.
  https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/agent-to-agent
* Foundry **Workflows** (``WorkflowAgentDefinition``) are portal/YAML-first (Power Fx based).
  The YAML is authored in the portal or VS Code Foundry Toolkit, registered as a workflow
  agent, then invoked by name via ``responses.create``.
  https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/workflow
* **Microsoft Agent Framework** (``agent-framework`` + ``agent-framework-foundry``) is the
  recommended pure-Python multi-agent path (``SequentialBuilder`` / ``HandoffBuilder`` over
  ``FoundryChatClient``), and runs against the same Responses API without portal A2A setup.
  https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from azure.ai.projects.models import (
    A2APreviewTool,
    PromptAgentDefinition,
    Tool,
    WorkflowAgentDefinition,
)

# Sub-agent slots, mirroring MultiAgentPipeline.agent_sequence (minus planner/conversation,
# which the orchestrator prompt itself plays in the A2A model).
A2A_SUB_AGENT_SLOTS: tuple[str, ...] = ("fsa-data", "fsa-research", "fsa-work-context", "fsa-report")

A2A_ORCHESTRATOR_INSTRUCTIONS = (
    "You orchestrate a quota-report pipeline for Wide World Importers. Call the connected "
    "sub-agents in order: first 'fsa-data' for governed sales rows (Fabric Data Agent or "
    "Databricks Genie), then 'fsa-research' for market intelligence, then 'fsa-work-context' "
    "for M365 activity, then 'fsa-report' to generate the XLSX/HTML/PDF artifacts. Synthesize "
    "their outputs into a single cited response."
)


def build_a2a_orchestrator_definition(
    *,
    model: str,
    sub_agent_connection_ids: Mapping[str, str],
    instructions: str = A2A_ORCHESTRATOR_INSTRUCTIONS,
) -> PromptAgentDefinition:
    """Build a Responses-API orchestrator that calls each sub-agent via the A2A preview tool.

    ``sub_agent_connection_ids`` maps a sub-agent slot name (e.g. ``"fsa-data"``) to the
    Foundry **project connection id** of that sub-agent's A2A endpoint. Create those
    connections in the Foundry portal first; there is no SDK-only path to register them as of
    2026 (see module docstring).

    The returned definition uses the exact same ``PromptAgentDefinition`` shape the single
    agent uses in ``foundry_agent.py``, so it registers with
    ``project_client.agents.create_version`` and runs through ``openai.responses.create`` —
    no classic threads/runs API involved.
    """

    if not model:
        raise ValueError("model must be a non-empty model deployment name.")
    if not sub_agent_connection_ids:
        raise ValueError("sub_agent_connection_ids must contain at least one sub-agent connection.")

    tools: list[A2APreviewTool] = []
    for slot_name, connection_id in sub_agent_connection_ids.items():
        if not connection_id:
            raise ValueError(f"Connection id for sub-agent '{slot_name}' must not be empty.")
        tools.append(
            A2APreviewTool(
                name=slot_name,
                description=f"A2A sub-agent for the '{slot_name}' stage of the quota pipeline.",
                project_connection_id=connection_id,
            )
        )

    return PromptAgentDefinition(
        model=model,
        instructions=instructions,
        tools=cast(list[Tool], tools),
    )


def build_workflow_agent_definition(workflow_yaml: str) -> WorkflowAgentDefinition:
    """Wrap a portal-authored Foundry Workflow YAML as a registrable workflow agent definition.

    Foundry Workflow YAML is Power Fx based and authored/exported from the Foundry portal or
    the VS Code Foundry Toolkit — this repo does not invent that schema. Pass the exported YAML
    string here to register it as a workflow agent version, then invoke it by name through the
    Responses API exactly like a prompt agent.
    """

    if not workflow_yaml.strip():
        raise ValueError("workflow_yaml must be a non-empty Foundry Workflow YAML document.")
    return WorkflowAgentDefinition(workflow=workflow_yaml)


def register_multi_agent_orchestrator(
    project_client: Any,
    *,
    agent_name: str,
    definition: PromptAgentDefinition | WorkflowAgentDefinition,
) -> Any:
    """Register an orchestrator/workflow definition as an agent version (live call).

    Requires Azure credentials and, for the A2A path, pre-created portal A2A connections.
    Mirrors the registration call used for the single agent in ``foundry_agent.py``.
    """

    return project_client.agents.create_version(agent_name=agent_name, definition=definition)
