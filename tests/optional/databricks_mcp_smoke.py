"""Real Databricks MCP transport: pytest tests/optional/databricks_mcp_smoke.py.

Requires the databricks-mcp extra; missing or incompatible packages fail collection.
HTTP delivery and workspace credentials are controlled offline, not live authorization.
"""

from __future__ import annotations

import json
import socket
from types import SimpleNamespace
from typing import Any

import databricks_mcp.mcp as databricks_mcp
import httpx2
import pytest

from src.orchestrator.databricks_genie import DatabricksGenieMcpClient, DatabricksGenieMcpConfig


@pytest.mark.parametrize("question_property", ["query", "question"])
def test_real_databricks_client_discovers_and_calls_mcp2_tool(
    monkeypatch: pytest.MonkeyPatch, question_property: str
) -> None:
    requests: list[dict[str, Any]] = []
    authenticated_requests: list[str] = []
    original_client = httpx2.AsyncClient
    original_connect = socket.socket.connect

    def loopback_only(sock: socket.socket, address: Any) -> None:
        # Windows asyncio needs a loopback socket pair; HTTP itself stays in MockTransport.
        if address[0] not in {"127.0.0.1", "::1"}:
            raise AssertionError("External network forbidden in the Databricks MCP smoke test")
        original_connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", loopback_only)

    def handle(request: httpx2.Request) -> httpx2.Response:
        assert request.headers["authorization"] == "Bearer offline-test-token"
        authenticated_requests.append(request.method)
        if request.method in {"GET", "DELETE"}:
            return httpx2.Response(405)
        payload = json.loads(request.content)
        requests.append(payload)
        if "id" not in payload:
            return httpx2.Response(202)
        method = payload["method"]
        if method == "server/discover":
            return httpx2.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "error": {"code": -32601, "message": "Method not found"},
                },
            )
        if method == "initialize":
            result = {
                "protocolVersion": payload["params"]["protocolVersion"],
                "serverInfo": {"name": "offline-genie", "version": "1"},
                "capabilities": {"tools": {}},
            }
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "query_genie",
                        "inputSchema": {
                            "type": "object",
                            "properties": {question_property: {"type": "string"}},
                            "required": [question_property],
                        },
                    }
                ]
            }
        elif method == "tools/call":
            assert payload["params"]["name"] == "query_genie"
            assert payload["params"]["arguments"] == {question_property: "sales"}
            result = {
                "content": [{"type": "text", "text": '[{"territory":"Northwest","revenue":42}]'}],
                "isError": False,
            }
        else:
            raise AssertionError(f"Unexpected MCP method: {method}")
        return httpx2.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": result})

    def http_client(**kwargs: Any) -> httpx2.AsyncClient:
        return original_client(transport=httpx2.MockTransport(handle), **kwargs)

    monkeypatch.setattr(databricks_mcp.httpx2, "AsyncClient", http_client)
    workspace = SimpleNamespace(
        config=SimpleNamespace(authenticate=lambda: {"Authorization": "Bearer offline-test-token"})
    )
    client = DatabricksGenieMcpClient(
        DatabricksGenieMcpConfig(mcp_url="https://workspace.invalid/api/2.0/mcp/genie/example"),
        workspace_client=workspace,
    )
    result = client.query("sales")

    assert result["status"] == "ok"
    assert result["transport"] == "managed-mcp"
    assert result["row_count"] == 1
    assert result["rows"] == [{"territory": "Northwest", "revenue": 42, "source_platform": "databricks"}]
    assert "Unity Catalog" in result["source"]
    methods = [request["method"] for request in requests]
    assert methods.index("initialize") < methods.index("tools/list") < methods.index("tools/call")
    assert "notifications/initialized" in methods
    assert authenticated_requests
