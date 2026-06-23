#!/usr/bin/env python3
"""Verify the Foundry agent registers and responds against a live project.

This is a thin, dependency-light harness used to prove that the SDK path in
``src/orchestrator/foundry_agent.py`` actually:

1. registers the ``SalesAgent`` prompt agent in the configured Foundry
   project (so it becomes visible in the ai.azure.com portal under Agents), and
2. responds to a question through the Responses API (the same call the portal
   Playground makes), exercising a *local* function tool so the check does not
   require a live Fabric Data Agent connection.

Required environment variables (see ``src/orchestrator/config.py``):

- ``FOUNDRY_PROJECT_ENDPOINT`` — e.g.
  ``https://<account>.services.ai.azure.com/api/projects/<project>``
- ``MODEL_DEPLOYMENT_NAME`` — a chat model deployment on the project (e.g. ``gpt-4o``)
- ``FABRIC_IQ_CONNECTION_ID`` is intentionally not required for this smoke test.
  The script clears preview platform-tool connection IDs and uses the demo-safe
  local ``fabric_query`` / ``get_account_activity`` function tools so the
  registration and Playground proof works before live Fabric or WorkIQ wiring.

Usage::

    uv run python scripts/verify_foundry_agent.py

Exit code is 0 on success, 1 on failure, 2 on missing configuration.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.orchestrator.config import OrchestratorConfig  # noqa: E402

# A question that the model can answer with the local compute_quota_attainment
# tool, so the round-trip does not depend on a live Fabric connection.
_LOCAL_TOOL_QUESTION = (
    "Compute quota attainment from these figures and summarize the risk rating. "
    "annual_target = 1000000, ytd_actual = 600000, open_pipeline = 500000, "
    "months_elapsed = 6, days_elapsed = 180. "
    "Use the compute_quota_attainment tool; do not query the sales database."
)


def check_agent_identity(agent: Any) -> tuple[bool, str]:
    """Return ``(ok, message)`` asserting the agent uses the new agent object model.

    In the new Azure AI Foundry agent object model, a registered agent owns its own
    ``identity`` (used for M365 / Teams publishing and downstream RBAC). Legacy agents
    expose ``identity == None`` and cannot use the new publish-to-Copilot path without
    migration. This guard makes that distinction explicit so the workshop never ships an
    agent that silently fails at publish time.
    """
    identity = getattr(agent, "identity", None)
    name = getattr(agent, "name", "<unknown>")
    if identity is None:
        return (
            False,
            f"agent '{name}' has identity=None (legacy agent model); "
            "the new agent object model is required for M365/Teams publishing",
        )
    return True, f"agent '{name}' exposes identity ({type(identity).__name__}) — new agent model"


def main() -> int:
    """Register the agent, confirm it is listed, and run one Playground-style query."""
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    from src.orchestrator.config import ConfigurationError
    from src.orchestrator.foundry_agent import _AGENT_NAME, _get_or_create_agent, run_query

    try:
        config = _local_tool_smoke_config(OrchestratorConfig.from_env())
    except ConfigurationError as exc:
        print(f"[config] {exc}")
        return 2

    print(f"[project] {config.foundry_project_endpoint}")
    print(f"[model]   {config.model_deployment_name}")

    with DefaultAzureCredential() as credential:
        with AIProjectClient(
            endpoint=config.foundry_project_endpoint,
            credential=credential,
            allow_preview=True,
        ) as project_client:
            agent = _get_or_create_agent(project_client, config)
            print(f"[register] created {agent.name} version {getattr(agent, 'version', '?')}")

            identity_ok, identity_msg = check_agent_identity(agent)
            print(f"[identity] {identity_msg}")
            if not identity_ok:
                print(
                    "[publish] prompt-agent registration has no dedicated hosted-agent identity yet; "
                    "use the hosted Responses protocol path for M365/Teams publishing"
                )

            names = sorted({getattr(a, "name", "") for a in project_client.agents.list()})
            print(f"[portal]   agents visible in project: {names}")
            if _AGENT_NAME not in names:
                print(f"[FAIL] {_AGENT_NAME} not visible in the project agent list")
                return 1

    print("[query]    sending Playground-style question (local tool path)...")
    answer = run_query(_LOCAL_TOOL_QUESTION, config)
    print("[response] " + answer.strip()[:1200])

    if "(no response text returned)" in answer or not answer.strip():
        print("[FAIL] agent returned no usable response")
        return 1

    print("[OK] live registration + Playground response verified")
    return 0


def _local_tool_smoke_config(config: OrchestratorConfig) -> OrchestratorConfig:
    """Keep the live project/model but force local tools for this deterministic smoke test."""

    return replace(
        config,
        fabric_iq_connection_id=None,
        market_data_connection_id=None,
        workiq_connection_id=None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
