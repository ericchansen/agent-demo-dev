"""Unit tests for the hosted Fabric MCP client."""

from __future__ import annotations

import json
import urllib.error
from io import BytesIO
from types import SimpleNamespace
from typing import Any

import pytest

from src.orchestrator.fabric_mcp_client import FabricMcpClient, FabricMcpConfigurationError, FabricMcpError


class _Credential:
    def get_token(self, *scopes: str) -> Any:
        return SimpleNamespace(token=f"token-for-{scopes[0]}")


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_fabric_mcp_client_requires_endpoint_and_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FABRIC_MCP_URL", raising=False)
    monkeypatch.delenv("FABRIC_MCP_TOOL_NAME", raising=False)

    with pytest.raises(FabricMcpConfigurationError, match="FABRIC_MCP_URL"):
        FabricMcpClient.from_env(credential=_Credential())

    monkeypatch.setenv("FABRIC_MCP_URL", "https://fabric.example/mcp")
    with pytest.raises(FabricMcpConfigurationError, match="FABRIC_MCP_TOOL_NAME"):
        FabricMcpClient.from_env(credential=_Credential())


def test_fabric_mcp_client_calls_tools_call(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: int) -> _Response:
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"content": [{"type": "text", "text": "Top customer is Tailspin Toys."}]},
            }
        )

    monkeypatch.setattr("src.orchestrator.fabric_mcp_client.urllib.request.urlopen", fake_urlopen)

    client = FabricMcpClient(
        endpoint_url="https://fabric.example/mcp",
        tool_name="ask_wwi",
        credential=_Credential(),
        timeout_seconds=7,
    )
    result = client.query("Top customers by revenue")

    assert result["status"] == "success"
    assert result["answer"] == "Top customer is Tailspin Toys."
    assert captured["url"] == "https://fabric.example/mcp"
    assert captured["timeout"] == 7
    assert captured["headers"]["Authorization"].startswith("Bearer token-for-")
    assert captured["body"]["method"] == "tools/call"
    assert captured["body"]["params"] == {"name": "ask_wwi", "arguments": {"question": "Top customers by revenue"}}


def test_fabric_mcp_client_surfaces_json_rpc_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(_request: Any, timeout: int) -> _Response:
        assert timeout == 120
        return _Response({"jsonrpc": "2.0", "id": 1, "error": {"message": "tool not found"}})

    monkeypatch.setattr("src.orchestrator.fabric_mcp_client.urllib.request.urlopen", fake_urlopen)
    client = FabricMcpClient(endpoint_url="https://fabric.example/mcp", tool_name="missing", credential=_Credential())

    with pytest.raises(FabricMcpError, match="tool not found"):
        client.query("Top customers")


def test_fabric_mcp_client_surfaces_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(_request: Any, timeout: int) -> _Response:
        assert timeout == 120
        raise urllib.error.HTTPError(
            url="https://fabric.example/mcp",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=BytesIO(b"missing token"),
        )

    monkeypatch.setattr("src.orchestrator.fabric_mcp_client.urllib.request.urlopen", fake_urlopen)
    client = FabricMcpClient(endpoint_url="https://fabric.example/mcp", tool_name="ask", credential=_Credential())

    with pytest.raises(FabricMcpError, match="HTTP 401"):
        client.query("Top customers")
