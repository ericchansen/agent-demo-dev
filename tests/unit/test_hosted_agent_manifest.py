"""Verify the Hosted Agent deployment manifest matches the server contract.

Azure AI Foundry Hosted Agents must declare a supported container protocol; a
bare ``/invoke`` route is not deployable on its own. These tests assert that
``agent.yaml`` exists, parses, and stays consistent with the routes and
request/response fields implemented in ``server.route_request``.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from src.orchestrator.hosted_agent import server

_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "src" / "orchestrator" / "hosted_agent" / "agent.yaml"


def _load_manifest() -> dict:
    with _MANIFEST_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    assert isinstance(data, dict)
    return data


def test_manifest_exists_and_parses() -> None:
    manifest = _load_manifest()
    assert manifest["name"]
    assert manifest["runtime"]["port"] == server.PORT


def test_declared_protocol_path_is_served() -> None:
    manifest = _load_manifest()
    protocols = manifest["protocols"]
    assert protocols, "at least one protocol must be declared"
    invocation = next(p for p in protocols if p["type"] == "invocations")
    declared_path = invocation["path"]

    # The declared invocation route must actually accept a POST on the server.
    status, _, _ = server.route_request(
        "POST",
        declared_path,
        {"Content-Type": "application/json"},
        b'{"input": "ping"}',
    )
    assert status != 404, f"declared protocol path {declared_path} is not served"


def test_request_response_fields_match_server() -> None:
    manifest = _load_manifest()
    invocation = next(p for p in manifest["protocols"] if p["type"] == "invocations")

    request_fields = set(invocation["request"]["fields"])
    assert {"input", "message"}.issubset(request_fields)

    response_field = invocation["response"]["field"]
    status, payload, _ = server.route_request(
        "POST",
        invocation["path"],
        {"Content-Type": "application/json"},
        b'{"input": "ping"}',
        invoke=lambda message: f"echo:{message}",
    )
    assert status == 200
    assert response_field in payload


def test_health_routes_match_manifest() -> None:
    manifest = _load_manifest()
    health = manifest["health"]
    for route in (health["liveness"], health["readiness"]):
        status, _, _ = server.route_request("GET", route, {}, b"")
        assert status == 200
