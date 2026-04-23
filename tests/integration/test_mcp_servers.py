"""Integration tests for the Researcher and SharePoint MCP servers.

These tests start each MCP server as a subprocess, communicate via stdio
using the MCP JSON-RPC protocol, and verify that the servers correctly
advertise their tools and handle tool invocations.

Run with:  pytest tests/integration/test_mcp_servers.py -m integration
Skip in fast CI by excluding the integration marker.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INITIALIZE_REQUEST: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "0.1.0"},
    },
}

_INITIALIZED_NOTIFICATION: dict[str, Any] = {
    "jsonrpc": "2.0",
    "method": "notifications/initialized",
}

_LIST_TOOLS_REQUEST: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {},
}


def _call_tool_request(tool_name: str, arguments: dict[str, Any], req_id: int = 3) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }


def _encode_message(msg: dict[str, Any]) -> bytes:
    """Encode a JSON-RPC message as newline-delimited JSON for MCP stdio transport."""
    return (json.dumps(msg) + "\n").encode()


async def _read_response(stdout: asyncio.StreamReader) -> dict[str, Any]:
    """Read a single JSON-RPC response line from the MCP server's stdout.

    The MCP Python SDK stdio transport uses newline-delimited JSON:
    one JSON-RPC message per line.
    """
    while True:
        line = await asyncio.wait_for(stdout.readline(), timeout=15)
        if not line:
            raise RuntimeError("MCP server closed stdout unexpectedly")
        decoded = line.decode().strip()
        if not decoded:
            continue
        return json.loads(decoded)


async def _start_mcp_server(module: str, env_overrides: dict[str, str] | None = None) -> asyncio.subprocess.Process:
    """Start an MCP server as a subprocess."""
    import os

    env = {**os.environ, **(env_overrides or {})}
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        module,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    return proc


async def _initialize_server(proc: asyncio.subprocess.Process) -> dict[str, Any]:
    """Send initialize + initialized notification, return the init response."""
    assert proc.stdin is not None
    assert proc.stdout is not None

    proc.stdin.write(_encode_message(_INITIALIZE_REQUEST))
    await proc.stdin.drain()

    response = await _read_response(proc.stdout)

    # Send the initialized notification (no response expected)
    proc.stdin.write(_encode_message(_INITIALIZED_NOTIFICATION))
    await proc.stdin.drain()

    # Small delay to let the server process the notification
    await asyncio.sleep(0.1)

    return response


async def _cleanup(proc: asyncio.subprocess.Process) -> None:
    """Terminate the server process cleanly."""
    if proc.returncode is None:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except TimeoutError:
            proc.kill()


# ---------------------------------------------------------------------------
# Researcher Agent Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_researcher_list_tools():
    """Researcher MCP server advertises the research_company tool."""
    proc = await _start_mcp_server(
        "src.agents.researcher.mcp_server",
        env_overrides={"SEARCH_PROVIDER": "mock"},
    )
    try:
        await _initialize_server(proc)

        assert proc.stdin is not None
        assert proc.stdout is not None

        proc.stdin.write(_encode_message(_LIST_TOOLS_REQUEST))
        await proc.stdin.drain()

        response = await _read_response(proc.stdout)

        assert "result" in response, f"Expected 'result' in response, got: {response}"
        tools = response["result"]["tools"]
        assert len(tools) >= 1

        tool_names = [t["name"] for t in tools]
        assert "research_company" in tool_names

        # Verify schema shape
        research_tool = next(t for t in tools if t["name"] == "research_company")
        assert "inputSchema" in research_tool
        assert "company_name" in research_tool["inputSchema"]["properties"]
    finally:
        await _cleanup(proc)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_researcher_call_tool_mock():
    """Researcher MCP server returns mock data for Tailspin Toys."""
    proc = await _start_mcp_server(
        "src.agents.researcher.mcp_server",
        env_overrides={"SEARCH_PROVIDER": "mock"},
    )
    try:
        await _initialize_server(proc)

        assert proc.stdin is not None
        assert proc.stdout is not None

        request = _call_tool_request("research_company", {"company_name": "Tailspin Toys"})
        proc.stdin.write(_encode_message(request))
        await proc.stdin.drain()

        response = await _read_response(proc.stdout)

        assert "result" in response, f"Expected 'result' in response, got: {response}"
        content = response["result"]["content"]
        assert len(content) >= 1
        assert content[0]["type"] == "text"

        data = json.loads(content[0]["text"])
        assert data["company_name"] == "Tailspin Toys"
        assert len(data["articles"]) > 0
        assert "key_metrics" in data
    finally:
        await _cleanup(proc)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_researcher_call_tool_unknown_company():
    """Researcher MCP server returns a generic response for an unknown company in mock mode."""
    proc = await _start_mcp_server(
        "src.agents.researcher.mcp_server",
        env_overrides={"SEARCH_PROVIDER": "mock"},
    )
    try:
        await _initialize_server(proc)

        assert proc.stdin is not None
        assert proc.stdout is not None

        request = _call_tool_request("research_company", {"company_name": "UnknownCorp"})
        proc.stdin.write(_encode_message(request))
        await proc.stdin.drain()

        response = await _read_response(proc.stdout)

        assert "result" in response
        data = json.loads(response["result"]["content"][0]["text"])
        assert data["company_name"] == "UnknownCorp"
        assert data["articles"] == []
    finally:
        await _cleanup(proc)


# ---------------------------------------------------------------------------
# SharePoint Agent Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sharepoint_list_tools():
    """SharePoint MCP server advertises search_documents and get_document_content tools."""
    proc = await _start_mcp_server(
        "src.agents.sharepoint.mcp_server",
        env_overrides={"SHAREPOINT_MODE": "mock"},
    )
    try:
        await _initialize_server(proc)

        assert proc.stdin is not None
        assert proc.stdout is not None

        proc.stdin.write(_encode_message(_LIST_TOOLS_REQUEST))
        await proc.stdin.drain()

        response = await _read_response(proc.stdout)

        assert "result" in response, f"Expected 'result' in response, got: {response}"
        tools = response["result"]["tools"]
        assert len(tools) >= 2

        tool_names = [t["name"] for t in tools]
        assert "search_documents" in tool_names
        assert "get_document_content" in tool_names

        # Verify schema for search_documents
        search_tool = next(t for t in tools if t["name"] == "search_documents")
        assert "query" in search_tool["inputSchema"]["properties"]
    finally:
        await _cleanup(proc)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sharepoint_search_documents_mock():
    """SharePoint MCP server returns mock documents for a matching query."""
    proc = await _start_mcp_server(
        "src.agents.sharepoint.mcp_server",
        env_overrides={"SHAREPOINT_MODE": "mock"},
    )
    try:
        await _initialize_server(proc)

        assert proc.stdin is not None
        assert proc.stdout is not None

        request = _call_tool_request("search_documents", {"query": "Tailspin"})
        proc.stdin.write(_encode_message(request))
        await proc.stdin.drain()

        response = await _read_response(proc.stdout)

        assert "result" in response, f"Expected 'result' in response, got: {response}"
        content = response["result"]["content"]
        assert len(content) >= 1
        assert content[0]["type"] == "text"

        data = json.loads(content[0]["text"])
        assert isinstance(data, list)
        assert len(data) > 0
        assert "name" in data[0]
        assert "Tailspin" in data[0]["name"]
    finally:
        await _cleanup(proc)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sharepoint_search_documents_no_results():
    """SharePoint MCP server returns an empty list for a non-matching query."""
    proc = await _start_mcp_server(
        "src.agents.sharepoint.mcp_server",
        env_overrides={"SHAREPOINT_MODE": "mock"},
    )
    try:
        await _initialize_server(proc)

        assert proc.stdin is not None
        assert proc.stdout is not None

        request = _call_tool_request("search_documents", {"query": "nonexistent-xyz-12345"})
        proc.stdin.write(_encode_message(request))
        await proc.stdin.drain()

        response = await _read_response(proc.stdout)

        assert "result" in response
        data = json.loads(response["result"]["content"][0]["text"])
        assert isinstance(data, list)
        assert len(data) == 0
    finally:
        await _cleanup(proc)
