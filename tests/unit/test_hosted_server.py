"""Unit tests for the hardened hosted-agent HTTP routing layer."""

from __future__ import annotations

import json

from src.orchestrator.hosted_agent import server


def _invoke_ok(message: str) -> str:
    return f"echo:{message}"


def test_legacy_root_health_is_preserved() -> None:
    status, payload, request_id = server.route_request("GET", "/", {}, b"")
    assert status == 200
    assert payload == {"status": "healthy", "agent": "wwi-sales-hosted"}
    assert request_id  # generated when absent


def test_healthz_liveness() -> None:
    status, payload, _ = server.route_request("GET", "/healthz", {}, b"")
    assert status == 200
    assert payload["status"] == "alive"


def test_readyz_reports_adapter() -> None:
    status, payload, _ = server.route_request("GET", "/readyz", {}, b"")
    assert status == 200
    assert payload["status"] == "ready"
    assert "adapter" in payload


def test_unknown_get_path_is_404() -> None:
    status, payload, _ = server.route_request("GET", "/nope", {}, b"")
    assert status == 404
    assert payload["error"] == "not_found"


def test_post_invocation_success() -> None:
    body = json.dumps({"input": "hello"}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    status, payload, _ = server.route_request("POST", "/invoke", headers, body, invoke=_invoke_ok)
    assert status == 200
    assert payload == {"output": "echo:hello"}


def test_post_accepts_message_alias_and_root_path() -> None:
    body = json.dumps({"message": "hi"}).encode("utf-8")
    status, payload, _ = server.route_request("POST", "/", {}, body, invoke=_invoke_ok)
    assert status == 200
    assert payload == {"output": "echo:hi"}


def test_invalid_json_returns_400() -> None:
    status, payload, _ = server.route_request("POST", "/invoke", {}, b"{not json", invoke=_invoke_ok)
    assert status == 400
    assert payload["error"] == "invalid_json"


def test_non_object_json_returns_400() -> None:
    status, payload, _ = server.route_request("POST", "/invoke", {}, b"[1, 2, 3]", invoke=_invoke_ok)
    assert status == 400
    assert payload["error"] == "invalid_payload"


def test_missing_input_returns_400() -> None:
    body = json.dumps({"input": "   "}).encode("utf-8")
    status, payload, _ = server.route_request("POST", "/invoke", {}, body, invoke=_invoke_ok)
    assert status == 400
    assert payload["error"] == "missing_input"


def test_payload_cap_returns_413() -> None:
    oversized = b"x" * (server.MAX_PAYLOAD_BYTES + 1)
    status, payload, _ = server.route_request("POST", "/invoke", {}, oversized, invoke=_invoke_ok)
    assert status == 413
    assert payload["error"] == "payload_too_large"


def test_wrong_content_type_returns_415() -> None:
    body = json.dumps({"input": "hi"}).encode("utf-8")
    headers = {"Content-Type": "text/plain"}
    status, payload, _ = server.route_request("POST", "/invoke", headers, body, invoke=_invoke_ok)
    assert status == 415
    assert payload["error"] == "unsupported_media_type"


def test_unknown_post_path_returns_404() -> None:
    body = json.dumps({"input": "hi"}).encode("utf-8")
    status, payload, _ = server.route_request("POST", "/other", {}, body, invoke=_invoke_ok)
    assert status == 404


def test_unsupported_method_returns_405() -> None:
    status, payload, _ = server.route_request("DELETE", "/", {}, b"")
    assert status == 405
    assert payload["error"] == "method_not_allowed"


def test_request_id_is_echoed_when_supplied() -> None:
    headers = {"X-Request-Id": "trace-123"}
    _, _, request_id = server.route_request("GET", "/healthz", headers, b"")
    assert request_id == "trace-123"


def test_request_id_lookup_is_case_insensitive() -> None:
    headers = {"x-request-id": "lower-456"}
    _, _, request_id = server.route_request("GET", "/healthz", headers, b"")
    assert request_id == "lower-456"


def test_invocation_failure_returns_500() -> None:
    def _boom(_: str) -> str:
        raise RuntimeError("kaboom")

    body = json.dumps({"input": "hi"}).encode("utf-8")
    status, payload, _ = server.route_request("POST", "/invoke", {}, body, invoke=_boom)
    assert status == 500
    assert payload["error"] == "internal_server_error"
