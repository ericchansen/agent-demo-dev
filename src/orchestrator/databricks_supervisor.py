"""Databricks Supervisor Agent request helpers for the quota workflow.

The Supervisor Agent is primarily configured in the Databricks UI. The Supervisor
API is the programmatic path, exposed through the Databricks OpenResponses-compatible
AI Gateway. This module keeps the workshop integration concrete without requiring
``databricks-openai`` during offline tests.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


class DatabricksSupervisorConfigurationError(Exception):
    """Raised when the Databricks Supervisor API client is not configured."""


@dataclass(frozen=True)
class SupervisorToolSpec:
    """One Databricks Supervisor API tool declaration.

    Every Supervisor tool object shares three top-level fields (``type``, optional
    ``name``, optional ``description``) plus a nested configuration object whose key
    matches the ``type`` discriminator. See the Databricks Supervisor API reference:
    https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-bricks/supervisor-api
    """

    type: str
    name: str
    config_key: str
    config: Mapping[str, object]
    description: str | None = None

    @classmethod
    def genie_space(cls, *, name: str, space_id: str, description: str | None = None) -> SupervisorToolSpec:
        """Create a Genie Space subagent tool."""

        _require_value("space_id", space_id)
        return cls(
            type="genie_space",
            name=name,
            config_key="genie_space",
            config={"space_id": space_id},
            description=description,
        )

    @classmethod
    def uc_function(cls, *, name: str, function_name: str, description: str | None = None) -> SupervisorToolSpec:
        """Create a Unity Catalog function tool."""

        _require_value("function_name", function_name)
        return cls(
            type="uc_function",
            name=name,
            config_key="uc_function",
            config={"name": function_name},
            description=description,
        )

    @classmethod
    def unity_catalog_table(cls, *, name: str, table_name: str, description: str | None = None) -> SupervisorToolSpec:
        """Create a Unity Catalog table tool."""

        _require_value("table_name", table_name)
        return cls(
            type="uc_table",
            name=name,
            config_key="uc_table",
            config={"name": table_name},
            description=description,
        )

    @classmethod
    def dashboard(cls, *, name: str, dashboard_id: str, description: str | None = None) -> SupervisorToolSpec:
        """Create an AI/BI dashboard tool.

        The Supervisor agent answers questions grounded in a published dashboard.
        """

        _require_value("dashboard_id", dashboard_id)
        return cls(
            type="dashboard",
            name=name,
            config_key="dashboard",
            config={"dashboard_id": dashboard_id},
            description=description,
        )

    @classmethod
    def knowledge_assistant(
        cls, *, name: str, knowledge_assistant_id: str, description: str | None = None
    ) -> SupervisorToolSpec:
        """Create a Knowledge Assistant subagent tool for unstructured retrieval."""

        _require_value("knowledge_assistant_id", knowledge_assistant_id)
        return cls(
            type="knowledge_assistant",
            name=name,
            config_key="knowledge_assistant",
            config={"knowledge_assistant_id": knowledge_assistant_id},
            description=description,
        )

    @classmethod
    def serving_endpoint(cls, *, name: str, endpoint_name: str, description: str | None = None) -> SupervisorToolSpec:
        """Create a tool that calls a custom agent served from a Model Serving endpoint."""

        _require_value("endpoint_name", endpoint_name)
        return cls(
            type="serving_endpoint",
            name=name,
            config_key="serving_endpoint",
            config={"name": endpoint_name},
            description=description,
        )

    def to_payload(self) -> dict[str, object]:
        """Return the OpenResponses-compatible Databricks tool payload."""

        _require_value("name", self.name)
        payload: dict[str, object] = {
            "type": self.type,
            "name": self.name,
            self.config_key: dict(self.config),
        }
        if self.description:
            payload["description"] = self.description
        return payload


@dataclass(frozen=True)
class SupervisorTraceDestination:
    """Unity Catalog destination for Supervisor API agent-loop traces.

    Passed to the Databricks client through ``extra_body`` so each request writes
    OpenTelemetry traces to ``<catalog>.<schema>.<table_prefix>*`` tables. See:
    https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-bricks/supervisor-api
    """

    catalog_name: str
    schema_name: str
    table_prefix: str

    def to_payload(self) -> dict[str, str]:
        """Return the ``trace_destination`` mapping for ``extra_body``."""

        _require_value("catalog_name", self.catalog_name)
        _require_value("schema_name", self.schema_name)
        _require_value("table_prefix", self.table_prefix)
        return {
            "catalog_name": self.catalog_name,
            "schema_name": self.schema_name,
            "table_prefix": self.table_prefix,
        }


@dataclass(frozen=True)
class SupervisorRequest:
    """A Databricks Supervisor API request payload."""

    model: str
    input: str | Sequence[Mapping[str, object]]
    tools: Sequence[SupervisorToolSpec]
    stream: bool = False
    trace_destination: SupervisorTraceDestination | None = None

    def to_payload(self) -> dict[str, object]:
        """Return a payload suitable for ``client.responses.create(**payload)``."""

        _require_value("model", self.model)
        if isinstance(self.input, str):
            _require_value("input", self.input)
            input_payload: object = [{"type": "message", "role": "user", "content": self.input}]
        else:
            input_payload = [dict(message) for message in self.input]
            if not input_payload:
                raise ValueError("input must contain at least one message.")

        tool_payloads = [tool.to_payload() for tool in self.tools]
        if not tool_payloads:
            raise ValueError("tools must contain at least one Supervisor tool.")

        payload: dict[str, object] = {
            "model": self.model,
            "input": input_payload,
            "tools": tool_payloads,
            "stream": self.stream,
        }
        if self.trace_destination is not None:
            payload["extra_body"] = {"trace_destination": self.trace_destination.to_payload()}
        return payload


class DatabricksSupervisorClient:
    """Thin wrapper around ``databricks_openai.DatabricksOpenAI``."""

    def __init__(self, client: Any | None = None) -> None:
        if client is not None:
            self._client = client
            return

        try:
            from databricks_openai import DatabricksOpenAI
        except ModuleNotFoundError as exc:  # pragma: no cover - optional live dependency.
            raise DatabricksSupervisorConfigurationError(
                "databricks-openai is not installed. Install it only for live Supervisor API calls."
            ) from exc

        self._client = DatabricksOpenAI(use_ai_gateway=True)

    def query(self, request: SupervisorRequest) -> Any:
        """Execute a Supervisor API request through AI Gateway."""

        return self._client.responses.create(**request.to_payload())


def build_quota_supervisor_request(
    question: str,
    *,
    customer_name: str = "Tailspin Toys",
    model: str | None = None,
    genie_space_id: str | None = None,
    quota_function_name: str | None = None,
    dashboard_id: str | None = None,
    knowledge_assistant_id: str | None = None,
    serving_endpoint_name: str | None = None,
    trace_destination: SupervisorTraceDestination | None = None,
) -> SupervisorRequest:
    """Build the Databricks-native multi-agent request for the quota workflow."""

    resolved_model = model or os.environ.get("DATABRICKS_SUPERVISOR_MODEL") or "databricks-claude-sonnet-4-5"
    tools: list[SupervisorToolSpec] = []
    if genie_space_id:
        tools.append(
            SupervisorToolSpec.genie_space(
                name="WWI sales Genie",
                space_id=genie_space_id,
                description="Answers governed sales questions over Unity Catalog using Genie SQL.",
            )
        )
    if quota_function_name:
        tools.append(
            SupervisorToolSpec.uc_function(
                name="Quota report function",
                function_name=quota_function_name,
                description="Computes quota methodology and attainment from governed UC data.",
            )
        )
    if dashboard_id:
        tools.append(
            SupervisorToolSpec.dashboard(
                name="Sales attainment dashboard",
                dashboard_id=dashboard_id,
                description="Grounds answers in the published AI/BI sales attainment dashboard.",
            )
        )
    if knowledge_assistant_id:
        tools.append(
            SupervisorToolSpec.knowledge_assistant(
                name="Sales playbook assistant",
                knowledge_assistant_id=knowledge_assistant_id,
                description="Retrieves unstructured quota methodology and playbook guidance.",
            )
        )
    if serving_endpoint_name:
        tools.append(
            SupervisorToolSpec.serving_endpoint(
                name="Custom quota agent",
                endpoint_name=serving_endpoint_name,
                description="Delegates to a custom agent served from a Model Serving endpoint.",
            )
        )
    if not tools:
        raise DatabricksSupervisorConfigurationError(
            "Configure at least one Databricks Supervisor tool: genie_space_id, quota_function_name, "
            "dashboard_id, knowledge_assistant_id, or serving_endpoint_name."
        )

    prompt = (
        f"Customer: {customer_name}\n"
        f"Task: {question.strip()}\n"
        "Use governed Unity Catalog data through the available tools. Return normalized sales evidence, "
        "quota methodology, scenario assumptions, and artifact recommendations."
    )
    return SupervisorRequest(model=resolved_model, input=prompt, tools=tools, trace_destination=trace_destination)


def _trace_destination_from_env() -> SupervisorTraceDestination | None:
    """Build a trace destination from ``DATABRICKS_SUPERVISOR_TRACE_*`` env vars, if all are set."""

    catalog = os.environ.get("DATABRICKS_SUPERVISOR_TRACE_CATALOG")
    schema = os.environ.get("DATABRICKS_SUPERVISOR_TRACE_SCHEMA")
    prefix = os.environ.get("DATABRICKS_SUPERVISOR_TRACE_TABLE_PREFIX")
    if catalog and schema and prefix:
        return SupervisorTraceDestination(catalog_name=catalog, schema_name=schema, table_prefix=prefix)
    return None


def databricks_supervisor_query_func(arguments: Mapping[str, object]) -> dict[str, object]:
    """Tool-style entry point that reports configuration gaps clearly."""

    question = str(arguments.get("question") or "").strip()
    if not question:
        raise ValueError("question must not be empty.")

    try:
        request = build_quota_supervisor_request(
            question,
            customer_name=str(arguments.get("customer_name") or "Tailspin Toys"),
            genie_space_id=os.environ.get("DATABRICKS_SUPERVISOR_GENIE_SPACE_ID"),
            quota_function_name=os.environ.get("DATABRICKS_SUPERVISOR_QUOTA_FUNCTION"),
            dashboard_id=os.environ.get("DATABRICKS_SUPERVISOR_DASHBOARD_ID"),
            knowledge_assistant_id=os.environ.get("DATABRICKS_SUPERVISOR_KNOWLEDGE_ASSISTANT_ID"),
            serving_endpoint_name=os.environ.get("DATABRICKS_SUPERVISOR_SERVING_ENDPOINT"),
            trace_destination=_trace_destination_from_env(),
        )
    except DatabricksSupervisorConfigurationError as exc:
        return {
            "status": "configuration_error",
            "message": str(exc),
            "required_environment": ["DATABRICKS_SUPERVISOR_GENIE_SPACE_ID or DATABRICKS_SUPERVISOR_QUOTA_FUNCTION"],
            "question": question,
        }

    response = DatabricksSupervisorClient().query(request)
    return {
        "status": "ok",
        "source": "Databricks Supervisor API backed by Unity Catalog",
        "request": request.to_payload(),
        "response": response,
    }


def _require_value(name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must not be empty.")
