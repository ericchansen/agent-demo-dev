#!/usr/bin/env python3
"""Stdio MCP proxy for Fabric Data Agent.

Bridges Copilot CLI (stdio) to the Fabric Data Agent MCP endpoint (HTTP)
using az CLI tokens for cross-tenant authentication.

The proxy is environment-driven so each workshop participant can point it at
their own Fabric workspace and Data Agent. Configure the endpoint either with a
full URL or with the workspace and data-agent IDs:

  FABRIC_MCP_URL          — full MCP endpoint URL (takes precedence if set)
  FABRIC_WORKSPACE_ID     — Fabric workspace GUID (used with FABRIC_DATA_AGENT_ID)
  FABRIC_DATA_AGENT_ID    — Fabric Data Agent GUID (used with FABRIC_WORKSPACE_ID)
  FABRIC_SUBSCRIPTION     — Azure subscription for `az account get-access-token` (required)
  FABRIC_TENANT           — tenant ID (optional, passed to az --tenant)
  FABRIC_RESOURCE         — OAuth resource scope (default: https://api.fabric.microsoft.com)
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request

_FABRIC_API_BASE = "https://api.fabric.microsoft.com"
_DEFAULT_RESOURCE = _FABRIC_API_BASE

TENANT = os.environ.get("FABRIC_TENANT", "")
RESOURCE = os.environ.get("FABRIC_RESOURCE", _DEFAULT_RESOURCE)

# Resolved at runtime in main() so importing the module never requires configuration.
MCP_URL = ""
SUBSCRIPTION = ""


def _resolve_mcp_url() -> str:
    """Return the Fabric MCP endpoint from env, preferring an explicit full URL."""
    explicit = os.environ.get("FABRIC_MCP_URL", "").strip()
    if explicit:
        return explicit
    workspace = os.environ.get("FABRIC_WORKSPACE_ID", "").strip()
    data_agent = os.environ.get("FABRIC_DATA_AGENT_ID", "").strip()
    if workspace and data_agent:
        return f"{_FABRIC_API_BASE}/v1/mcp/workspaces/{workspace}/dataagents/{data_agent}/agent"
    raise SystemExit(
        "[fabric-proxy] No Fabric endpoint configured. Set FABRIC_MCP_URL, or set both "
        "FABRIC_WORKSPACE_ID and FABRIC_DATA_AGENT_ID, to point the proxy at your Fabric Data Agent."
    )


def _resolve_subscription() -> str:
    """Return the Azure subscription used for token acquisition, or fail with guidance."""
    subscription = os.environ.get("FABRIC_SUBSCRIPTION", "").strip()
    if not subscription:
        raise SystemExit(
            "[fabric-proxy] FABRIC_SUBSCRIPTION is not set. Set it to the Azure subscription ID "
            "that `az account get-access-token` should use for the Fabric resource scope."
        )
    return subscription


# Cross-platform: Windows needs "az.cmd", Unix uses "az" directly
_AZ_CMD = "az.cmd" if platform.system() == "Windows" else "az"

_token_cache: dict[str, object] = {"token": None, "expires": 0.0}


def _log(msg: str) -> None:
    """Write diagnostic messages to stderr (invisible to MCP protocol)."""
    print(f"[fabric-proxy] {msg}", file=sys.stderr, flush=True)


def get_token() -> str:
    """Acquire or return cached Fabric access token via az CLI."""
    now = time.time()
    if _token_cache["token"] and float(str(_token_cache["expires"])) > now + 60:
        return str(_token_cache["token"])

    cmd = [
        _AZ_CMD,
        "account",
        "get-access-token",
        "--resource",
        RESOURCE,
        "--subscription",
        SUBSCRIPTION,
        "--query",
        "accessToken",
        "-o",
        "tsv",
    ]
    if TENANT:
        cmd.extend(["--tenant", TENANT])

    _log(f"Acquiring token (subscription={SUBSCRIPTION[:8]}...)")
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    _token_cache["token"] = result.stdout.strip()
    _token_cache["expires"] = now + 3000  # ~50 min
    _log("Token acquired successfully")
    return str(_token_cache["token"])


def forward_request(request: dict[str, object]) -> dict[str, object]:
    """Forward a JSON-RPC request to the Fabric MCP endpoint."""
    token = get_token()
    data = json.dumps(request).encode()
    req = urllib.request.Request(
        MCP_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    method = request.get("method", "?")
    _log(f"→ {method} (id={request.get('id')})")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as http_err:
        # Fabric may return JSON-RPC error bodies with non-200 status codes
        err_body = http_err.read().decode(errors="replace")
        _log(f"← {method} HTTP {http_err.code}: {err_body[:200]}")
        try:
            return dict(json.loads(err_body))
        except (json.JSONDecodeError, TypeError):
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32603, "message": f"HTTP {http_err.code}: {err_body[:500]}"},
            }

    _log(f"← {method} OK")
    return dict(body)


def main() -> None:
    """Main loop — read JSON-RPC from stdin, proxy to Fabric, write to stdout."""
    global MCP_URL, SUBSCRIPTION
    MCP_URL = _resolve_mcp_url()
    SUBSCRIPTION = _resolve_subscription()
    _log(f"Starting proxy → {MCP_URL[:60]}...")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            _log(f"Skipping non-JSON input: {line[:80]}")
            continue

        # JSON-RPC notifications have no "id" and expect no response.
        if "id" not in request:
            _log(f"Notification (no id): {request.get('method', '?')} — skipping response")
            continue

        try:
            response = forward_request(request)
        except subprocess.CalledProcessError as exc:
            _log(f"az CLI failed: {exc.stderr}")
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32603, "message": f"Token acquisition failed: {exc.stderr}"},
            }
        except Exception as exc:
            _log(f"Request failed: {exc}")
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32603, "message": str(exc)},
            }

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
