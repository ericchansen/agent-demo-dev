"""Unit tests for the hosted Fabric MCP client."""

from __future__ import annotations

import json
import urllib.error
from io import BytesIO
from types import SimpleNamespace
from typing import Any

import pytest

from src.orchestrator.fabric_mcp_client import (
    FabricMcpClient,
    FabricMcpConfigurationError,
    FabricMcpError,
    build_fabric_credential,
    fabric_spn_status,
)

_FABRIC_SPN_ENV_VARS = ("FABRIC_CLIENT_ID", "FABRIC_CLIENT_SECRET", "FABRIC_TENANT_ID")


def _clear_fabric_spn_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _FABRIC_SPN_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


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
    monkeypatch.delenv("FABRIC_WORKSPACE_ID", raising=False)
    monkeypatch.delenv("FABRIC_DATA_AGENT_ID", raising=False)

    with pytest.raises(FabricMcpConfigurationError, match="FABRIC_MCP_URL"):
        FabricMcpClient.from_env(credential=_Credential())

    monkeypatch.setenv("FABRIC_MCP_URL", "https://fabric.example/mcp")
    client = FabricMcpClient.from_env(credential=_Credential())
    assert client.endpoint_url == "https://fabric.example/mcp"
    assert client.tool_name is None


def test_fabric_mcp_client_builds_endpoint_from_workspace_and_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FABRIC_MCP_URL", raising=False)
    monkeypatch.setenv("FABRIC_WORKSPACE_ID", "workspace-123")
    monkeypatch.setenv("FABRIC_DATA_AGENT_ID", "agent-456")
    monkeypatch.setenv("FABRIC_MCP_TOOL_NAME", "ask_wwi")

    client = FabricMcpClient.from_env(credential=_Credential())

    assert (
        client.endpoint_url
        == "https://api.fabric.microsoft.com/v1/mcp/workspaces/workspace-123/dataagents/agent-456/agent"
    )
    assert client.tool_name == "ask_wwi"


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


def test_fabric_mcp_client_discovers_single_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    bodies: list[dict[str, Any]] = []

    def fake_urlopen(request: Any, timeout: int) -> _Response:
        assert timeout == 120
        body = json.loads(request.data.decode("utf-8"))
        bodies.append(body)
        if body["method"] == "tools/list":
            return _Response({"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": "ask_wwi"}]}})
        return _Response({"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": "OK"}]}})

    monkeypatch.setattr("src.orchestrator.fabric_mcp_client.urllib.request.urlopen", fake_urlopen)
    client = FabricMcpClient(endpoint_url="https://fabric.example/mcp", tool_name=None, credential=_Credential())

    result = client.query("Top customers")

    assert result["tool_name"] == "ask_wwi"
    assert result["answer"] == "OK"
    assert [body["method"] for body in bodies] == ["tools/list", "tools/call"]


def test_fabric_mcp_client_requires_tool_name_when_multiple_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(_request: Any, timeout: int) -> _Response:
        assert timeout == 120
        return _Response(
            {"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": "ask_wwi"}, {"name": "ask_market"}]}}
        )

    monkeypatch.setattr("src.orchestrator.fabric_mcp_client.urllib.request.urlopen", fake_urlopen)
    client = FabricMcpClient(endpoint_url="https://fabric.example/mcp", tool_name=None, credential=_Credential())

    with pytest.raises(FabricMcpConfigurationError, match="FABRIC_MCP_TOOL_NAME"):
        client.query("Top customers")


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


def test_fabric_spn_status_defaults_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_fabric_spn_env(monkeypatch)

    assert fabric_spn_status() == ("default", [])


def test_fabric_spn_status_service_principal_when_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FABRIC_CLIENT_ID", "client-1")
    monkeypatch.setenv("FABRIC_CLIENT_SECRET", "secret-1")
    monkeypatch.setenv("FABRIC_TENANT_ID", "tenant-1")

    assert fabric_spn_status() == ("service-principal", [])


def test_fabric_spn_status_reports_missing_when_partial(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_fabric_spn_env(monkeypatch)
    monkeypatch.setenv("FABRIC_CLIENT_ID", "client-1")

    mode, missing = fabric_spn_status()

    assert mode == "partial"
    assert missing == ["FABRIC_CLIENT_SECRET", "FABRIC_TENANT_ID"]


def test_build_fabric_credential_uses_default_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_fabric_spn_env(monkeypatch)
    captured: dict[str, Any] = {}

    def fake_default(*args: Any, **kwargs: Any) -> str:
        captured["default"] = True
        return "default-credential"

    monkeypatch.setattr("src.orchestrator.fabric_mcp_client.DefaultAzureCredential", fake_default)

    assert build_fabric_credential() == "default-credential"
    assert captured["default"] is True


def test_build_fabric_credential_uses_client_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FABRIC_CLIENT_ID", "client-1")
    monkeypatch.setenv("FABRIC_CLIENT_SECRET", "secret-1")
    monkeypatch.setenv("FABRIC_TENANT_ID", "tenant-1")
    captured: dict[str, Any] = {}

    def fake_client_secret(*, tenant_id: str, client_id: str, client_secret: str) -> str:
        captured.update(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
        return "spn-credential"

    monkeypatch.setattr("src.orchestrator.fabric_mcp_client.ClientSecretCredential", fake_client_secret)

    assert build_fabric_credential() == "spn-credential"
    assert captured == {"tenant_id": "tenant-1", "client_id": "client-1", "client_secret": "secret-1"}


def test_build_fabric_credential_rejects_partial_config(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_fabric_spn_env(monkeypatch)
    monkeypatch.setenv("FABRIC_TENANT_ID", "tenant-1")

    with pytest.raises(FabricMcpConfigurationError, match="FABRIC_CLIENT_ID"):
        build_fabric_credential()


def test_from_env_selects_service_principal_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FABRIC_MCP_URL", "https://fabric.example/mcp")
    monkeypatch.delenv("FABRIC_MCP_TOOL_NAME", raising=False)
    monkeypatch.setenv("FABRIC_CLIENT_ID", "client-1")
    monkeypatch.setenv("FABRIC_CLIENT_SECRET", "secret-1")
    monkeypatch.setenv("FABRIC_TENANT_ID", "tenant-1")

    monkeypatch.setattr(
        "src.orchestrator.fabric_mcp_client.ClientSecretCredential",
        lambda **_kwargs: "spn-credential",
    )

    client = FabricMcpClient.from_env()

    assert client.credential == "spn-credential"
