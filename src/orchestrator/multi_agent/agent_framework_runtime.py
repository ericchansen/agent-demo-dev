"""Optional Microsoft Agent Framework runtime for the quota multi-agent path.

Two runtimes back the multi-agent pipeline, selected by the
``WWI_MULTI_AGENT_RUNTIME`` environment variable (or the ``--runtime`` CLI flag):

- ``deterministic`` (the default) is a fully **offline** pipeline that mirrors the
  single-agent quota flow with fixed routing. It makes **no model call** and needs
  **no Azure credentials**, producing identical artifacts on every run. This is the
  path exercised by CI and offline demos; a green run is *not* proof that a live model
  was invoked.
- ``agent-framework`` is the **live** path implemented here. It requires the optional
  ``agent-framework`` extra, a Foundry project endpoint, a model deployment, and
  ``DefaultAzureCredential``. Only this runtime actually invokes a model.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from src.orchestrator.multi_agent.pipeline import AgentRegistration, MultiAgentPipeline

AGENT_FRAMEWORK_RUNTIME_ENV = "WWI_MULTI_AGENT_RUNTIME"


class AgentFrameworkUnavailableError(RuntimeError):
    """Raised when the optional Microsoft Agent Framework packages are unavailable."""


class AgentFrameworkConfigurationError(RuntimeError):
    """Raised when the Agent Framework runtime is selected without required settings."""


@dataclass(frozen=True)
class AgentFrameworkAdapters:
    """Import bundle for dependency injection in offline tests."""

    agent_cls: type[Any]
    chat_client_cls: type[Any]
    sequential_builder_cls: type[Any]
    handoff_builder_cls: type[Any]
    credential_factory: Callable[[], Any]


@dataclass(frozen=True)
class AgentFrameworkStage:
    """One participant in the Agent Framework workflow."""

    registration: AgentRegistration
    instructions: str


@dataclass(frozen=True)
class AgentFrameworkHandoff:
    """Allowed control transfer between participants in the handoff workflow."""

    source: str
    targets: tuple[str, ...]


@dataclass(frozen=True)
class AgentFrameworkWorkflowSpec:
    """Framework workflow shape shared by sequential and handoff builders."""

    stages: tuple[AgentFrameworkStage, ...]
    handoffs: tuple[AgentFrameworkHandoff, ...]


def load_agent_framework_adapters() -> AgentFrameworkAdapters:
    """Load optional Agent Framework imports only when the runtime is requested."""

    try:
        from agent_framework import Agent
        from agent_framework.foundry import FoundryChatClient
        from agent_framework.orchestrations import HandoffBuilder, SequentialBuilder
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        raise AgentFrameworkUnavailableError(
            "Install the optional runtime with `uv sync --extra agent-framework` "
            'or `pip install -e ".[agent-framework]"`.'
        ) from exc

    return AgentFrameworkAdapters(
        agent_cls=Agent,
        chat_client_cls=FoundryChatClient,
        sequential_builder_cls=SequentialBuilder,
        handoff_builder_cls=HandoffBuilder,
        credential_factory=DefaultAzureCredential,
    )


def build_quota_workflow_spec(data_source: str = "fabric") -> AgentFrameworkWorkflowSpec:
    """Return the Agent Framework participants for the WWI quota workflow."""

    platform = "Databricks Genie / Unity Catalog" if data_source == "databricks" else "Fabric Data Agent"
    registrations = {agent.name: agent for agent in MultiAgentPipeline.agent_sequence}
    stages = (
        AgentFrameworkStage(
            registrations["planner"],
            "You are the planner for a quota workflow. Break the request into data, research, "
            "work-context, analysis, and report steps. Route work to the right specialist.",
        ),
        AgentFrameworkStage(
            registrations["data"],
            f"You are the data agent. Use {platform} sales data and return governed rows, source citations, "
            "and any data-quality caveats.",
        ),
        AgentFrameworkStage(
            registrations["research"],
            "You are the research agent. Add market context, competitive signals, and risks that affect quota.",
        ),
        AgentFrameworkStage(
            registrations["work-context"],
            "You are the work-context agent. Add relevant WorkIQ or M365 engagement context without exposing PII.",
        ),
        AgentFrameworkStage(
            registrations["conversational"],
            "You are the analysis agent. Synthesize the prior outputs into a concise quota recommendation.",
        ),
        AgentFrameworkStage(
            registrations["report"],
            "You are the report agent. Summarize the report artifacts that should be generated and cite inputs.",
        ),
    )
    handoffs = (
        AgentFrameworkHandoff("planner", ("data", "research", "work-context")),
        AgentFrameworkHandoff("data", ("conversational",)),
        AgentFrameworkHandoff("research", ("conversational",)),
        AgentFrameworkHandoff("work-context", ("conversational",)),
        AgentFrameworkHandoff("conversational", ("report",)),
    )
    return AgentFrameworkWorkflowSpec(stages=stages, handoffs=handoffs)


def build_foundry_chat_client(
    *,
    project_endpoint: str | None = None,
    model: str | None = None,
    adapters: AgentFrameworkAdapters | None = None,
) -> Any:
    """Create a FoundryChatClient using the env names from both Foundry samples and this repo."""

    resolved_endpoint = project_endpoint or os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    resolved_model = model or os.environ.get("FOUNDRY_MODEL") or os.environ.get("MODEL_DEPLOYMENT_NAME")
    missing = []
    if not resolved_endpoint:
        missing.append("FOUNDRY_PROJECT_ENDPOINT")
    if not resolved_model:
        missing.append("FOUNDRY_MODEL or MODEL_DEPLOYMENT_NAME")
    if missing:
        raise AgentFrameworkConfigurationError(
            "Missing required Agent Framework environment variables: " + ", ".join(missing)
        )

    resolved_adapters = adapters or load_agent_framework_adapters()
    return resolved_adapters.chat_client_cls(
        project_endpoint=resolved_endpoint,
        model=resolved_model,
        credential=resolved_adapters.credential_factory(),
    )


def build_sequential_workflow(
    *,
    client: Any,
    data_source: str = "fabric",
    adapters: AgentFrameworkAdapters | None = None,
) -> Any:
    """Build the Microsoft Agent Framework sequential workflow."""

    resolved_adapters = adapters or load_agent_framework_adapters()
    spec = build_quota_workflow_spec(data_source)
    agents = [
        resolved_adapters.agent_cls(
            client=client,
            instructions=stage.instructions,
            name=stage.registration.foundry_agent_name,
        )
        for stage in spec.stages
    ]
    return resolved_adapters.sequential_builder_cls(participants=agents, output_from="all").build()


def build_handoff_workflow(
    *,
    client: Any,
    data_source: str = "fabric",
    adapters: AgentFrameworkAdapters | None = None,
) -> Any:
    """Build the Agent Framework handoff workflow for portal-style agent routing."""

    resolved_adapters = adapters or load_agent_framework_adapters()
    spec = build_quota_workflow_spec(data_source)
    agents_by_name = {
        stage.registration.name: resolved_adapters.agent_cls(
            client=client,
            instructions=stage.instructions,
            name=stage.registration.foundry_agent_name,
            require_per_service_call_history_persistence=True,
        )
        for stage in spec.stages
    }
    start_agent = agents_by_name["planner"]
    builder = resolved_adapters.handoff_builder_cls(
        name="wwi_quota_handoff",
        participants=list(agents_by_name.values()),
        termination_condition=lambda conversation: bool(
            conversation and "report" in (getattr(conversation[-1], "text", "") or "").lower()
        ),
    ).with_start_agent(start_agent)

    add_handoff = getattr(builder, "add_handoff", None)
    if callable(add_handoff):
        for handoff in spec.handoffs:
            targets = [agents_by_name[target] for target in handoff.targets]
            builder = add_handoff(agents_by_name[handoff.source], targets)

    return builder.build()


async def run_agent_framework_pipeline_async(
    user_message: str,
    *,
    customer_name: str = "Wide World Importers",
    data_source: str = "fabric",
    project_endpoint: str | None = None,
    model: str | None = None,
    adapters: AgentFrameworkAdapters | None = None,
) -> dict[str, object]:
    """Run the optional Agent Framework sequential workflow against FoundryChatClient."""

    resolved_adapters = adapters or load_agent_framework_adapters()
    client = build_foundry_chat_client(project_endpoint=project_endpoint, model=model, adapters=resolved_adapters)
    workflow = build_sequential_workflow(client=client, data_source=data_source, adapters=resolved_adapters)
    prompt = (
        f"Customer: {customer_name}\n"
        f"Data source: {data_source}\n"
        f"Task: {user_message}\n"
        "Return the quota recommendation, handoff summary, and report artifact plan."
    )
    result = await workflow.run(prompt)
    outputs = _extract_output_texts(result)
    return {
        "runtime": "agent-framework",
        "orchestration": "sequential",
        "customer_name": customer_name,
        "data_source": data_source,
        "response": "\n\n".join(outputs) if outputs else str(result),
        "stage_outputs": outputs,
        "agent_sequence": [
            {
                "name": agent.name,
                "role": agent.role,
                "foundry_agent_name": agent.foundry_agent_name,
            }
            for agent in MultiAgentPipeline.agent_sequence
        ],
    }


def run_agent_framework_pipeline(
    user_message: str,
    *,
    customer_name: str = "Wide World Importers",
    data_source: str = "fabric",
    project_endpoint: str | None = None,
    model: str | None = None,
) -> dict[str, object]:
    """Synchronous command-friendly wrapper for the optional Agent Framework runtime."""

    return asyncio.run(
        run_agent_framework_pipeline_async(
            user_message,
            customer_name=customer_name,
            data_source=data_source,
            project_endpoint=project_endpoint,
            model=model,
        )
    )


def resolve_multi_agent_runtime(cli_runtime: str | None = None) -> str:
    """Resolve the runtime switch. Deterministic remains the safe default."""

    runtime = (cli_runtime or os.environ.get(AGENT_FRAMEWORK_RUNTIME_ENV) or "deterministic").strip().lower()
    if runtime not in {"deterministic", "agent-framework"}:
        raise ValueError(f"Unsupported multi-agent runtime '{runtime}'. Use 'deterministic' or 'agent-framework'.")
    return runtime


def _extract_output_texts(result: Any) -> list[str]:
    get_outputs = getattr(result, "get_outputs", None)
    raw_outputs: Sequence[Any]
    if callable(get_outputs):
        raw_outputs = list(get_outputs())
    elif isinstance(result, Sequence) and not isinstance(result, str):
        raw_outputs = result
    else:
        raw_outputs = [result]

    texts: list[str] = []
    for output in raw_outputs:
        text = getattr(output, "text", None)
        if isinstance(text, str) and text.strip():
            texts.append(text.strip())
            continue
        messages = getattr(output, "messages", None)
        if messages is not None:
            texts.extend(
                message_text.strip()
                for message in messages
                if isinstance((message_text := getattr(message, "text", None)), str) and message_text.strip()
            )
            continue
        output_text = str(output).strip()
        if output_text:
            texts.append(output_text)
    return texts
