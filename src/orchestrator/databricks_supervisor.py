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
    """One Databricks Supervisor API tool declaration."""

    type: str
    name: str
    config_key: str
    config: Mapping[str, object]

    @classmethod
    def genie_space(cls, *, name: str, space_id: str) -> SupervisorToolSpec:
        """Create a Genie Space subagent tool."""

        _require_value("space_id", space_id)
        return cls(type="genie_space", name=name, config_key="genie_space", config={"space_id": space_id})

    @classmethod
    def uc_function(cls, *, name: str, function_name: str) -> SupervisorToolSpec:
        """Create a Unity Catalog function tool."""

        _require_value("function_name", function_name)
        return cls(type="uc_function", name=name, config_key="uc_function", config={"name": function_name})

    @classmethod
    def unity_catalog_table(cls, *, name: str, table_name: str) -> SupervisorToolSpec:
        """Create a Unity Catalog table tool."""

        _require_value("table_name", table_name)
        return cls(type="uc_table", name=name, config_key="uc_table", config={"name": table_name})

    def to_payload(self) -> dict[str, object]:
        """Return the OpenResponses-compatible Databricks tool payload."""

        _require_value("name", self.name)
        return {
            "type": self.type,
            "name": self.name,
            self.config_key: dict(self.config),
        }


@dataclass(frozen=True)
class SupervisorRequest:
    """A Databricks Supervisor API request payload."""

    model: str
    input: str | Sequence[Mapping[str, object]]
    tools: Sequence[SupervisorToolSpec]
    stream: bool = False

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

        return {
            "model": self.model,
            "input": input_payload,
            "tools": tool_payloads,
            "stream": self.stream,
        }


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
) -> SupervisorRequest:
    """Build the Databricks-native multi-agent request for the quota workflow."""

    resolved_model = model or os.environ.get("DATABRICKS_SUPERVISOR_MODEL") or "databricks-claude-sonnet-4-5"
    tools: list[SupervisorToolSpec] = []
    if genie_space_id:
        tools.append(SupervisorToolSpec.genie_space(name="WWI sales Genie", space_id=genie_space_id))
    if quota_function_name:
        tools.append(
            SupervisorToolSpec.uc_function(
                name="Quota report function",
                function_name=quota_function_name,
            )
        )
    if not tools:
        raise DatabricksSupervisorConfigurationError(
            "Configure at least one Databricks Supervisor tool: genie_space_id or quota_function_name."
        )

    prompt = (
        f"Customer: {customer_name}\n"
        f"Task: {question.strip()}\n"
        "Use governed Unity Catalog data through the available tools. Return normalized sales evidence, "
        "quota methodology, scenario assumptions, and artifact recommendations."
    )
    return SupervisorRequest(model=resolved_model, input=prompt, tools=tools)


def databricks_supervisor_query_func(arguments: Mapping[str, object]) -> dict[str, object]:
    """Tool-style entry point that reports configuration gaps clearly."""

    question = str(arguments.get("question") or "").strip()
    if not question:
        raise ValueError("question must not be empty.")

    genie_space_id = os.environ.get("DATABRICKS_SUPERVISOR_GENIE_SPACE_ID")
    quota_function_name = os.environ.get("DATABRICKS_SUPERVISOR_QUOTA_FUNCTION")
    try:
        request = build_quota_supervisor_request(
            question,
            customer_name=str(arguments.get("customer_name") or "Tailspin Toys"),
            genie_space_id=genie_space_id,
            quota_function_name=quota_function_name,
        )
    except DatabricksSupervisorConfigurationError as exc:
        return {
            "status": "configuration_error",
            "message": str(exc),
            "required_environment": [
                "DATABRICKS_SUPERVISOR_GENIE_SPACE_ID or DATABRICKS_SUPERVISOR_QUOTA_FUNCTION"
            ],
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
