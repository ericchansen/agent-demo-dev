"""Managed-identity client for Fabric Data Agent MCP endpoints."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from azure.identity import DefaultAzureCredential

_FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
_DEFAULT_TIMEOUT_SECONDS = 120


class TokenCredential(Protocol):
    """Small protocol for Azure token credentials used by the client."""

    def get_token(self, *scopes: str) -> Any:
        """Return an access token for the supplied scopes."""


class FabricMcpConfigurationError(RuntimeError):
    """Raised when the Fabric MCP endpoint is not configured."""


class FabricMcpError(RuntimeError):
    """Raised when a Fabric MCP request fails."""


@dataclass(frozen=True)
class FabricMcpClient:
    """Call a Fabric Data Agent MCP tool over HTTP JSON-RPC."""

    endpoint_url: str
    tool_name: str | None
    credential: TokenCredential
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls, credential: TokenCredential | None = None) -> FabricMcpClient:
        """Build a client from hosted-agent environment variables."""
        endpoint_url = _resolve_endpoint_url()
        tool_name = os.environ.get("FABRIC_MCP_TOOL_NAME", "").strip() or None
        if not endpoint_url:
            raise FabricMcpConfigurationError(
                "Fabric MCP endpoint is not configured. Set FABRIC_MCP_URL, or set both "
                "FABRIC_WORKSPACE_ID and FABRIC_DATA_AGENT_ID."
            )
        return cls(
            endpoint_url=endpoint_url,
            tool_name=tool_name,
            credential=credential or DefaultAzureCredential(),
        )

    def query(self, question: str) -> dict[str, Any]:
        """Ask the configured Fabric MCP tool a natural-language question."""
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("question is required.")

        tool_name = self.tool_name or self.discover_tool_name()
        result = self.call_tool({"question": normalized_question}, tool_name=tool_name)
        return {
            "status": "success",
            "source": "Fabric Data Agent MCP",
            "tool_name": tool_name,
            "question": normalized_question,
            "answer": _extract_answer(result),
            "raw_result": result,
        }

    def list_tools(self) -> list[dict[str, Any]]:
        """Return available MCP tools from the configured endpoint."""
        response = self._post_json_rpc(method="tools/list", params={}, request_id=1)
        result = response.get("result")
        tools = result.get("tools") if isinstance(result, dict) else None
        if not isinstance(tools, list):
            raise FabricMcpError("Fabric MCP tools/list response did not include a tools array.")
        return [tool for tool in tools if isinstance(tool, dict)]

    def discover_tool_name(self) -> str:
        """Pick the only available Fabric MCP tool, or ask the operator to configure one explicitly."""
        tools = self.list_tools()
        names = sorted(str(tool.get("name")) for tool in tools if tool.get("name"))
        if len(names) == 1:
            return names[0]
        if not names:
            raise FabricMcpConfigurationError(
                "Fabric MCP endpoint returned no tools. Confirm the Data Agent is published as an MCP server."
            )
        raise FabricMcpConfigurationError(
            "FABRIC_MCP_TOOL_NAME is required because the Fabric MCP endpoint exposes multiple tools: "
            + ", ".join(names)
        )

    def call_tool(self, arguments: dict[str, Any], *, tool_name: str | None = None) -> dict[str, Any]:
        """Invoke the configured MCP tool via the standard tools/call method."""
        resolved_tool_name = tool_name or self.tool_name
        if not resolved_tool_name:
            raise FabricMcpConfigurationError("FABRIC_MCP_TOOL_NAME is not configured.")
        response = self._post_json_rpc(
            method="tools/call",
            params={"name": resolved_tool_name, "arguments": arguments},
            request_id=2,
        )
        result = response.get("result")
        if not isinstance(result, dict):
            raise FabricMcpError("Fabric MCP response did not include an object result.")
        return result

    def _post_json_rpc(self, *, method: str, params: dict[str, Any], request_id: int) -> dict[str, Any]:
        token = str(self.credential.get_token(_FABRIC_SCOPE).token)
        body = json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint_url,
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode(errors="replace")
            raise FabricMcpError(f"Fabric MCP HTTP {exc.code}: {error_body[:500]}") from exc
        except urllib.error.URLError as exc:
            raise FabricMcpError(f"Fabric MCP request failed: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise FabricMcpError("Fabric MCP returned invalid JSON.") from exc

        if not isinstance(payload, dict):
            raise FabricMcpError("Fabric MCP returned a non-object JSON-RPC payload.")
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message", "Unknown Fabric MCP error")
            raise FabricMcpError(str(message))
        return payload


def _resolve_endpoint_url() -> str:
    explicit = os.environ.get("FABRIC_MCP_URL", "").strip()
    if explicit:
        return explicit
    workspace_id = os.environ.get("FABRIC_WORKSPACE_ID", "").strip()
    data_agent_id = os.environ.get("FABRIC_DATA_AGENT_ID", "").strip()
    if workspace_id and data_agent_id:
        return f"https://api.fabric.microsoft.com/v1/mcp/workspaces/{workspace_id}/dataagents/{data_agent_id}/agent"
    return ""


def _extract_answer(result: dict[str, Any]) -> str:
    content = result.get("content")
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
        if text_parts:
            return "\n".join(text_parts)

    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        for key in ("answer", "result", "text", "content"):
            value = structured.get(key)
            if isinstance(value, str) and value:
                return value

    return json.dumps(result, ensure_ascii=False)
