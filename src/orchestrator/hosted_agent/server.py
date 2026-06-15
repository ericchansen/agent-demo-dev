"""Foundry invocation server for the Hosted Agent.

Receives HTTP POST requests from the Foundry managed runtime and dispatches
them to the agent pipeline. The routing logic lives in :func:`route_request`,
a transport-free function that maps an HTTP method/path/headers/body to a
status code and JSON payload so it can be unit tested without opening sockets.

Endpoints:
    GET  /          -> legacy health payload (preserved for existing probes)
    GET  /healthz   -> liveness probe
    GET  /readyz    -> readiness probe (reports adapter selection)
    POST /          -> agent invocation (alias of /invoke)
    POST /invoke    -> agent invocation
    POST /responses -> OpenAI-compatible Responses protocol for Hosted Agents

Every response carries an ``X-Request-Id`` header: the inbound value is echoed
when supplied, otherwise a fresh UUID is generated for log correlation.

Reference: https://github.com/microsoft-foundry/foundry-samples
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable, Mapping
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from src.orchestrator.hosted_agent import build_adapter, process_invocation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PORT = 8080
REQUEST_ID_HEADER = "X-Request-Id"
#: Reject invocation bodies larger than this to bound memory use (1 MiB).
MAX_PAYLOAD_BYTES = 1_048_576

InvokeFn = Callable[[str], str]
_RESPONSES_ROUTES = {"/responses", "/openai/responses", "/v1/responses"}


def _header(headers: Mapping[str, str], name: str) -> str | None:
    """Case-insensitive header lookup tolerant of plain dicts and HTTP messages."""
    getter = getattr(headers, "get", None)
    if callable(getter):
        value = headers.get(name)
        if value is not None:
            return value
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return None


def resolve_request_id(headers: Mapping[str, str]) -> str:
    """Return the inbound request id or mint a new one for correlation."""
    incoming = _header(headers, REQUEST_ID_HEADER)
    if incoming:
        return incoming.strip()[:128]
    return str(uuid.uuid4())


def _readiness_detail() -> str:
    """Describe which adapter the runtime will use; the local runtime is always available."""
    try:
        adapter = build_adapter()
    except Exception as exc:  # noqa: BLE001 - readiness must never raise
        return f"local-runtime (adapter unavailable: {type(exc).__name__})"
    return type(adapter).__name__ if adapter is not None else "local-runtime"


def _extract_response_input(payload: dict[str, Any]) -> str:
    """Return the latest user text from an OpenAI Responses-style payload."""
    raw_input = payload.get("input", payload.get("message", ""))
    if isinstance(raw_input, str):
        return raw_input.strip()

    if isinstance(raw_input, list):
        chunks: list[str] = []
        for item in raw_input:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            if role not in (None, "user"):
                continue
            content = item.get("content", "")
            if isinstance(content, str):
                chunks.append(content)
                continue
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        text = part.get("text") or part.get("content")
                        if isinstance(text, str):
                            chunks.append(text)
        return "\n".join(chunk for chunk in chunks if chunk.strip()).strip()

    return ""


def _responses_payload(result: str, request_id: str, model: str | None = None) -> dict[str, Any]:
    """Build a compact non-streaming Responses API payload."""
    response_key = request_id.replace("-", "")[:24]
    return {
        "id": f"resp_{response_key}",
        "object": "response",
        "created_at": 0,
        "status": "completed",
        "model": model or "wwi-hosted-agent",
        "output_text": result,
        "output": [
            {
                "id": f"msg_{response_key}",
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": result,
                    }
                ],
            }
        ],
    }


def route_request(
    method: str,
    path: str,
    headers: Mapping[str, str],
    body: bytes,
    *,
    invoke: InvokeFn = process_invocation,
) -> tuple[int, dict[str, Any], str]:
    """Map a request to ``(status_code, json_payload, request_id)`` without any I/O."""
    request_id = resolve_request_id(headers)
    route = path.split("?", 1)[0].rstrip("/") or "/"

    if method == "GET":
        if route == "/healthz":
            return 200, {"status": "alive"}, request_id
        if route == "/readyz":
            return 200, {"status": "ready", "adapter": _readiness_detail()}, request_id
        if route == "/":
            return 200, {"status": "healthy", "agent": "wwi-sales-hosted"}, request_id
        return 404, {"error": "not_found", "path": route}, request_id

    if method == "POST":
        if route not in ("/", "/invoke", *_RESPONSES_ROUTES):
            return 404, {"error": "not_found", "path": route}, request_id

        if len(body) > MAX_PAYLOAD_BYTES:
            return (
                413,
                {"error": "payload_too_large", "max_bytes": MAX_PAYLOAD_BYTES},
                request_id,
            )

        content_type = _header(headers, "Content-Type") or ""
        if content_type and "application/json" not in content_type.lower():
            return (
                415,
                {"error": "unsupported_media_type", "expected": "application/json"},
                request_id,
            )

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return 400, {"error": "invalid_json"}, request_id

        if not isinstance(payload, dict):
            return 400, {"error": "invalid_payload", "expected": "json object"}, request_id

        if route in _RESPONSES_ROUTES:
            if payload.get("stream") is True:
                return 400, {"error": "streaming_not_supported", "expected": "stream=false"}, request_id
            user_message = _extract_response_input(payload)
        else:
            user_message = str(payload.get("input", payload.get("message", ""))).strip()
        if not user_message:
            return (
                400,
                {"error": "missing_input", "expected": "non-empty 'input' or 'message'"},
                request_id,
            )

        try:
            result = invoke(user_message)
        except Exception:
            logger.exception("Invocation failed (request_id=%s)", request_id)
            return 500, {"error": "internal_server_error"}, request_id
        if route in _RESPONSES_ROUTES:
            return 200, _responses_payload(result, request_id, str(payload.get("model") or "")), request_id
        return 200, {"output": result}, request_id

    return 405, {"error": "method_not_allowed", "method": method}, request_id


class InvocationHandler(BaseHTTPRequestHandler):
    """Handle Foundry agent invocation and health requests."""

    server_version = "WWIHostedAgent/1.0"

    def _dispatch(self, method: str) -> None:
        content_length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(content_length) if content_length > 0 else b""
        headers = dict(self.headers.items())
        status, payload, request_id = route_request(method, self.path, headers, body)
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header(REQUEST_ID_HEADER, request_id)
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self) -> None:  # noqa: N802
        """Process an agent invocation."""
        self._dispatch("POST")

    def do_GET(self) -> None:  # noqa: N802
        """Serve health and readiness probes."""
        self._dispatch("GET")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Route access logs through the module logger instead of stderr."""
        logger.info("%s - %s", self.address_string(), format % args)


def main() -> None:
    """Start the invocation server."""
    logger.info("Hosted Agent adapter selection: %s", _readiness_detail())
    server = HTTPServer(("0.0.0.0", PORT), InvocationHandler)
    logger.info("Hosted Agent server starting on port %d", PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
