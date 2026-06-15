"""Databricks Genie client and row normalizer for the quota pipeline."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


class DatabricksGenieConfigurationError(Exception):
    """Raised when the Databricks Genie client is not configured."""


class DatabricksGenieError(Exception):
    """Raised when a Genie query completes without usable tabular rows."""


@dataclass(frozen=True)
class DatabricksGenieConfig:
    """Environment-backed settings for a Genie Space."""

    workspace_url: str
    space_id: str
    warehouse_id: str | None = None

    @classmethod
    def from_env(cls) -> DatabricksGenieConfig:
        """Build Genie configuration from standard Databricks environment variables."""

        workspace_url = os.environ.get("DATABRICKS_WORKSPACE_URL") or os.environ.get("DATABRICKS_HOST")
        space_id = os.environ.get("DATABRICKS_GENIE_SPACE_ID")
        warehouse_id = os.environ.get("DATABRICKS_GENIE_WAREHOUSE_ID") or os.environ.get("DATABRICKS_WAREHOUSE_ID")

        missing = [
            name
            for name, value in (
                ("DATABRICKS_WORKSPACE_URL", workspace_url),
                ("DATABRICKS_GENIE_SPACE_ID", space_id),
            )
            if not value
        ]
        if missing:
            raise DatabricksGenieConfigurationError(
                f"Missing required Databricks Genie environment variables: {', '.join(missing)}."
            )

        assert workspace_url is not None
        assert space_id is not None
        normalized_url = workspace_url.rstrip("/")
        if not normalized_url.startswith("https://"):
            raise DatabricksGenieConfigurationError("DATABRICKS_WORKSPACE_URL must be an https:// workspace URL.")

        return cls(workspace_url=normalized_url, space_id=space_id, warehouse_id=warehouse_id)


class DatabricksGenieClient:
    """Thin adapter around ``WorkspaceClient.genie`` that returns normalized quota rows."""

    def __init__(self, config: DatabricksGenieConfig, workspace_client: Any | None = None) -> None:
        self.config = config
        if workspace_client is not None:
            self._workspace = workspace_client
            return

        try:
            from databricks.sdk import WorkspaceClient
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency is installed in normal environments.
            raise DatabricksGenieConfigurationError(
                "databricks-sdk is not installed. Run 'uv sync --extra dev' before using Databricks Genie."
            ) from exc

        self._workspace = WorkspaceClient(host=config.workspace_url)

    @classmethod
    def from_env(cls) -> DatabricksGenieClient:
        """Create a client from environment variables."""

        return cls(DatabricksGenieConfig.from_env())

    def query(self, question: str, *, conversation_id: str | None = None) -> dict[str, object]:
        """Ask Genie a natural-language question and return normalized tabular rows."""

        clean_question = question.strip()
        if not clean_question:
            raise ValueError("question must not be empty.")

        genie = self._workspace.genie
        if conversation_id:
            message = genie.create_message_and_wait(
                space_id=self.config.space_id,
                conversation_id=conversation_id,
                content=clean_question,
            )
            resolved_conversation_id = conversation_id
        else:
            message = genie.start_conversation_and_wait(space_id=self.config.space_id, content=clean_question)
            resolved_conversation_id = _read_field(message, "conversation_id", "conversation.id") or ""

        message_id = str(_read_field(message, "message_id", "id") or "")
        rows = self._extract_rows(message, str(resolved_conversation_id), message_id)
        response_text = _read_field(message, "content", "text", "message")

        return {
            "status": "ok",
            "source": "Databricks Genie Space backed by Unity Catalog",
            "workspace_url": self.config.workspace_url,
            "space_id": self.config.space_id,
            "conversation_id": str(resolved_conversation_id),
            "message_id": message_id,
            "question": clean_question,
            "rows": rows,
            "row_count": len(rows),
            "response_text": response_text if isinstance(response_text, str) else "",
        }

    def _extract_rows(self, message: Any, conversation_id: str, message_id: str) -> list[dict[str, object]]:
        attachments = _as_sequence(_read_field(message, "attachments", "message.attachments"))
        rows: list[dict[str, object]] = []

        for attachment in attachments:
            inline_rows = _rows_from_query_result(_read_field(attachment, "query_result", "result"))
            if inline_rows:
                rows.extend(inline_rows)
                continue

            attachment_id = _read_field(attachment, "attachment_id", "id")
            if not attachment_id:
                continue

            query_result = self._workspace.genie.get_message_query_result(
                space_id=self.config.space_id,
                conversation_id=conversation_id,
                message_id=message_id,
                attachment_id=str(attachment_id),
            )
            rows.extend(_rows_from_query_result(query_result))

        return [_with_databricks_source(row) for row in rows]


@dataclass(frozen=True)
class DatabricksGenieMcpConfig:
    """Settings for the Databricks managed MCP Genie server.

    The managed MCP Genie endpoint has the shape
    ``https://<workspace-hostname>/api/2.0/mcp/genie/<space_id>`` and enforces
    Unity Catalog permissions server-side. Authentication is handled by the
    Databricks SDK unified auth chain (PAT via ``DATABRICKS_TOKEN``, OAuth M2M via
    ``DATABRICKS_CLIENT_ID`` / ``DATABRICKS_CLIENT_SECRET``, or a U2M CLI profile).
    """

    mcp_url: str
    workspace_url: str | None = None

    @classmethod
    def from_env(cls) -> DatabricksGenieMcpConfig:
        """Build managed-MCP configuration from environment variables."""

        mcp_url = os.environ.get("DATABRICKS_GENIE_MCP_URL")
        if not mcp_url:
            raise DatabricksGenieConfigurationError(
                "Missing required Databricks Genie environment variable: DATABRICKS_GENIE_MCP_URL."
            )

        normalized_mcp_url = mcp_url.rstrip("/")
        if not normalized_mcp_url.startswith("https://"):
            raise DatabricksGenieConfigurationError("DATABRICKS_GENIE_MCP_URL must be an https:// endpoint.")

        workspace_url = os.environ.get("DATABRICKS_WORKSPACE_URL") or os.environ.get("DATABRICKS_HOST")
        if workspace_url:
            workspace_url = workspace_url.rstrip("/")
        else:
            parsed = urlparse(normalized_mcp_url)
            workspace_url = f"https://{parsed.hostname}" if parsed.hostname else None

        return cls(mcp_url=normalized_mcp_url, workspace_url=workspace_url)


class DatabricksGenieMcpClient:
    """Adapter around the Databricks managed MCP Genie server.

    Selected only when ``DATABRICKS_GENIE_MCP_URL`` is configured. It discovers the
    Genie query tool exposed by the managed server, calls it, and normalizes the
    returned content into the same quota-row shape the SDK-direct client produces.
    """

    def __init__(
        self,
        config: DatabricksGenieMcpConfig,
        mcp_client: Any | None = None,
        workspace_client: Any | None = None,
    ) -> None:
        self.config = config
        if mcp_client is not None:
            self._mcp = mcp_client
            return

        try:
            from databricks_mcp import DatabricksMCPClient
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency installed in normal environments.
            raise DatabricksGenieConfigurationError(
                "databricks-mcp is not installed. Run 'uv sync --extra dev' before using the managed MCP path."
            ) from exc

        if workspace_client is None:
            try:
                from databricks.sdk import WorkspaceClient
            except ModuleNotFoundError as exc:  # pragma: no cover - dependency installed in normal environments.
                raise DatabricksGenieConfigurationError(
                    "databricks-sdk is not installed. Run 'uv sync --extra dev' before using the managed MCP path."
                ) from exc
            workspace_client = WorkspaceClient(host=self.config.workspace_url)

        self._mcp = DatabricksMCPClient(server_url=self.config.mcp_url, workspace_client=workspace_client)

    @classmethod
    def from_env(cls) -> DatabricksGenieMcpClient:
        """Create a managed-MCP client from environment variables."""

        return cls(DatabricksGenieMcpConfig.from_env())

    def query(self, question: str, *, tool_name: str | None = None) -> dict[str, object]:
        """Ask the managed MCP Genie server a question and return normalized rows."""

        clean_question = question.strip()
        if not clean_question:
            raise ValueError("question must not be empty.")

        tools = _as_sequence(self._mcp.list_tools())
        tool = _select_genie_tool(tools, tool_name)
        if tool is None:
            raise DatabricksGenieError(
                f"The Databricks Genie MCP server at {self.config.mcp_url} exposed no callable tools."
            )

        resolved_tool_name = str(_read_field(tool, "name") or "")
        arguments = _build_mcp_tool_arguments(tool, clean_question)
        response = self._mcp.call_tool(resolved_tool_name, arguments)

        response_text = _join_mcp_text(response)
        rows = _rows_from_mcp_payload(_parse_mcp_payload(response_text))

        return {
            "status": "ok",
            "source": "Databricks Genie managed MCP server backed by Unity Catalog",
            "transport": "managed-mcp",
            "mcp_url": self.config.mcp_url,
            "tool_name": resolved_tool_name,
            "question": clean_question,
            "rows": rows,
            "row_count": len(rows),
            "response_text": response_text,
        }


def databricks_genie_query_func(arguments: dict[str, Any]) -> dict[str, object]:
    """Tool handler that queries Genie or returns a clear configuration/error payload.

    Transport selection is explicit and non-breaking:

    * When ``DATABRICKS_GENIE_MCP_URL`` is set, the Databricks **managed MCP** Genie
      server is used (Unity Catalog permissions enforced server-side).
    * Otherwise the existing **SDK-direct** Genie Conversation API path is used.
    """

    question = str(arguments.get("question", "")).strip()
    conversation_id = arguments.get("conversation_id")
    if conversation_id is not None and not isinstance(conversation_id, str):
        raise ValueError("conversation_id must be a string when provided.")

    if os.environ.get("DATABRICKS_GENIE_MCP_URL"):
        try:
            return DatabricksGenieMcpClient.from_env().query(question)
        except DatabricksGenieConfigurationError as exc:
            return {
                "status": "configuration_error",
                "message": str(exc),
                "required_environment": ["DATABRICKS_GENIE_MCP_URL"],
                "question": question,
            }
        except DatabricksGenieError as exc:
            return {"status": "error", "message": str(exc), "question": question}

    try:
        return DatabricksGenieClient.from_env().query(question, conversation_id=conversation_id)
    except DatabricksGenieConfigurationError as exc:
        return {
            "status": "configuration_error",
            "message": str(exc),
            "required_environment": ["DATABRICKS_WORKSPACE_URL", "DATABRICKS_GENIE_SPACE_ID"],
            "question": question,
        }
    except DatabricksGenieError as exc:
        return {"status": "error", "message": str(exc), "question": question}


def _with_databricks_source(row: Mapping[str, object]) -> dict[str, object]:
    normalized = dict(row)
    normalized.setdefault("source_platform", "databricks")
    return normalized


_QUESTION_PROPERTY_NAMES = (
    "query",
    "question",
    "prompt",
    "content",
    "text",
    "message",
    "nl_query",
    "natural_language_query",
)


def _select_genie_tool(tools: Sequence[Any], tool_name: str | None) -> Any | None:
    """Pick the Genie query tool from the MCP tool list."""

    if not tools:
        return None
    if tool_name:
        for tool in tools:
            if str(_read_field(tool, "name") or "") == tool_name:
                return tool
        return None

    def _looks_like_query(tool: Any) -> bool:
        name = str(_read_field(tool, "name") or "").lower()
        if any(keyword in name for keyword in ("genie", "query", "ask")):
            return True
        properties = _read_field(tool, "inputSchema.properties", "input_schema.properties")
        if isinstance(properties, Mapping):
            return any(prop in properties for prop in _QUESTION_PROPERTY_NAMES)
        return False

    for tool in tools:
        if _looks_like_query(tool):
            return tool
    return tools[0]


def _build_mcp_tool_arguments(tool: Any, question: str) -> dict[str, object]:
    """Map the natural-language question onto the tool's input schema."""

    properties = _read_field(tool, "inputSchema.properties", "input_schema.properties")
    if isinstance(properties, Mapping):
        for prop in _QUESTION_PROPERTY_NAMES:
            if prop in properties:
                return {prop: question}
        string_props = [
            name
            for name, schema in properties.items()
            if isinstance(schema, Mapping) and schema.get("type") == "string"
        ]
        if len(string_props) == 1:
            return {string_props[0]: question}
    return {"query": question}


def _join_mcp_text(response: Any) -> str:
    """Concatenate the text parts of an MCP ``call_tool`` response."""

    content = _read_field(response, "content")
    parts: list[str] = []
    for item in _as_sequence(content):
        text = _read_field(item, "text")
        if isinstance(text, str):
            parts.append(text)
        elif isinstance(item, str):
            parts.append(item)
    if parts:
        return "".join(parts)
    if isinstance(content, str):
        return content
    return ""


def _parse_mcp_payload(text: str) -> Any:
    """Parse MCP tool text content as JSON, tolerating non-JSON responses."""

    candidate = text.strip()
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None


def _rows_from_mcp_payload(payload: Any) -> list[dict[str, object]]:
    """Normalize a parsed MCP payload into quota rows tagged with the Databricks source."""

    rows: list[dict[str, object]]
    if isinstance(payload, list):
        columns = list(payload[0].keys()) if payload and isinstance(payload[0], Mapping) else []
        rows = _normalize_rows(payload, columns)
    elif isinstance(payload, Mapping):
        rows = _rows_from_query_result(payload)
        if not rows:
            nested = payload.get("rows") or payload.get("data") or payload.get("records")
            rows = _normalize_rows(nested, _column_names(payload))
    else:
        rows = []
    return [_with_databricks_source(row) for row in rows]


def _rows_from_query_result(query_result: Any) -> list[dict[str, object]]:
    if query_result is None:
        return []

    candidates = [
        query_result,
        _read_field(query_result, "statement_response"),
        _read_field(query_result, "statement_response.result"),
        _read_field(query_result, "result"),
        _read_field(query_result, "data"),
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        rows = _read_field(candidate, "rows", "data_array", "data")
        if rows is None and isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes, bytearray)):
            rows = candidate
        columns = _column_names(candidate) or _column_names(query_result)
        extracted = _normalize_rows(rows, columns)
        if extracted:
            return extracted
    return []


def _normalize_rows(rows: Any, columns: Sequence[str]) -> list[dict[str, object]]:
    values = _as_sequence(rows)
    if not values:
        return []

    normalized: list[dict[str, object]] = []
    for row in values:
        if isinstance(row, Mapping):
            normalized.append(dict(row))
            continue
        cells = _as_sequence(row)
        if cells and columns:
            normalized.append({columns[index]: cell for index, cell in enumerate(cells[: len(columns)])})
    return normalized


def _column_names(value: Any) -> list[str]:
    schema = _read_field(
        value,
        "schema",
        "manifest.schema",
        "result.schema",
        "result.manifest.schema",
        "statement_response.manifest.schema",
        "statement_response.result.schema",
    )
    columns = _read_field(value, "columns") or _read_field(schema, "columns")
    names: list[str] = []
    for index, column in enumerate(_as_sequence(columns)):
        name = _read_field(column, "name", "display_name")
        names.append(str(name) if name else f"column_{index + 1}")
    return names


def _read_field(value: Any, *paths: str) -> Any:
    for path in paths:
        current = value
        found = True
        for part in path.split("."):
            if isinstance(current, Mapping):
                current = current.get(part)
            else:
                current = getattr(current, part, None)
            if current is None:
                found = False
                break
        if found:
            return current
    return None


def _as_sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, (str, bytes, bytearray)):
        return []
    if isinstance(value, Sequence):
        return list(value)
    return []
