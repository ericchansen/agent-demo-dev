"""Unit tests for the Foundry verify harness new-agent-model identity guard."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

_MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "verify_foundry_agent.py"
_spec = importlib.util.spec_from_file_location("verify_foundry_agent", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
verify_foundry_agent = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify_foundry_agent)


def test_check_agent_identity_passes_for_new_model() -> None:
    agent = SimpleNamespace(name="WWISalesAgent", identity=SimpleNamespace(type="ManagedIdentity"))
    ok, message = verify_foundry_agent.check_agent_identity(agent)
    assert ok is True
    assert "new agent model" in message


def test_check_agent_identity_fails_for_legacy_model() -> None:
    agent = SimpleNamespace(name="WWISalesAgent", identity=None)
    ok, message = verify_foundry_agent.check_agent_identity(agent)
    assert ok is False
    assert "legacy agent model" in message


def test_check_agent_identity_handles_missing_attribute() -> None:
    agent = SimpleNamespace(name="WWISalesAgent")
    ok, _ = verify_foundry_agent.check_agent_identity(agent)
    assert ok is False
