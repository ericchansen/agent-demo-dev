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
    assert manifest["kind"] == "hosted"
    assert manifest["resources"]["cpu"]


def test_declared_protocol_path_is_served() -> None:
    manifest = _load_manifest()
    protocols = manifest["protocols"]
    assert protocols, "at least one protocol must be declared"
    declared = {p["protocol"] for p in protocols}
    assert {"responses", "invocations"}.issubset(declared)

    # The declared protocol routes must actually accept POSTs on the server.
    for route in ("/responses", "/invoke"):
        status, _, _ = server.route_request(
            "POST",
            route,
            {"Content-Type": "application/json"},
            b'{"input": "ping"}',
        )
        assert status != 404, f"declared protocol route {route} is not served"


def test_request_response_fields_match_server() -> None:
    manifest = _load_manifest()
    assert any(p["protocol"] == "invocations" for p in manifest["protocols"])

    status, payload, _ = server.route_request(
        "POST",
        "/invoke",
        {"Content-Type": "application/json"},
        b'{"input": "ping"}',
        invoke=lambda message: f"echo:{message}",
    )
    assert status == 200
    assert payload["output"] == "echo:ping"


def test_responses_protocol_returns_openai_compatible_payload() -> None:
    status, payload, _ = server.route_request(
        "POST",
        "/responses",
        {"Content-Type": "application/json"},
        b'{"input": [{"role": "user", "content": "ping"}], "model": "gpt-4o"}',
        invoke=lambda message: f"echo:{message}",
    )

    assert status == 200
    assert payload["object"] == "response"
    assert payload["status"] == "completed"
    assert payload["model"] == "gpt-4o"
    assert payload["output_text"] == "echo:ping"
    assert payload["output"][0]["content"][0]["text"] == "echo:ping"


def test_health_routes_match_manifest() -> None:
    manifest = _load_manifest()
    health = manifest["health"]
    for route in (health["liveness"], health["readiness"]):
        status, _, _ = server.route_request("GET", route, {}, b"")
        assert status == 200
