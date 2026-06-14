#!/usr/bin/env python3
"""Stdio MCP proxy for Fabric Data Agent.

Bridges Copilot CLI (stdio) to the Fabric Data Agent MCP endpoint (HTTP)
using az CLI tokens for cross-tenant authentication.

Environment variables (override defaults):
  FABRIC_MCP_URL          — full MCP endpoint URL
  FABRIC_SUBSCRIPTION     — Azure subscription for token acquisition
  FABRIC_TENANT           — tenant ID (passed to az --tenant)
  FABRIC_RESOURCE         — OAuth resource scope (default: https://api.fabric.microsoft.com)
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
import urllib.request

_DEFAULT_MCP_URL = (
    "https://api.fabric.microsoft.com/v1/mcp/workspaces/"
    "6cf857b8-a0d0-4029-af88-62a83b4116e5/dataagents/"
    "f89ca52e-8d23-4020-b0ab-489ab57d0d14/agent"
)
_DEFAULT_SUBSCRIPTION = "9450bd3b-96c5-48b2-bfdf-3374304efbd7"
_DEFAULT_RESOURCE = "https://api.fabric.microsoft.com"

MCP_URL = os.environ.get("FABRIC_MCP_URL", _DEFAULT_MCP_URL)
SUBSCRIPTION = os.environ.get("FABRIC_SUBSCRIPTION", _DEFAULT_SUBSCRIPTION)
TENANT = os.environ.get("FABRIC_TENANT", "")
RESOURCE = os.environ.get("FABRIC_RESOURCE", _DEFAULT_RESOURCE)

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

    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read())

    _log(f"← {method} OK")
    return dict(body)


def main() -> None:
    """Main loop — read JSON-RPC from stdin, proxy to Fabric, write to stdout."""
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
