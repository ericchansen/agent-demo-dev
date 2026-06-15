"""Databricks Genie client and row normalizer for the quota pipeline."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


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


def databricks_genie_query_func(arguments: dict[str, Any]) -> dict[str, object]:
    """Tool handler that queries Genie or returns a clear configuration/error payload."""

    question = str(arguments.get("question", "")).strip()
    conversation_id = arguments.get("conversation_id")
    if conversation_id is not None and not isinstance(conversation_id, str):
        raise ValueError("conversation_id must be a string when provided.")

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
        extracted = _normalize_rows(rows, _column_names(candidate))
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
    schema = _read_field(value, "schema", "manifest.schema")
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
