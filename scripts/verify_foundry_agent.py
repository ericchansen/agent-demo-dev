#!/usr/bin/env python3
"""Verify the WWI Foundry agent registers and responds against a live project.

This is a thin, dependency-light harness used to prove that the SDK path in
``src/orchestrator/foundry_agent.py`` actually:

1. registers the ``WWISalesAgent`` prompt agent in the configured Foundry
   project (so it becomes visible in the ai.azure.com portal under Agents), and
2. responds to a question through the Responses API (the same call the portal
   Playground makes), exercising a *local* function tool so the check does not
   require a live Fabric Data Agent connection.

Required environment variables (see ``src/orchestrator/config.py``):

- ``FOUNDRY_PROJECT_ENDPOINT`` — e.g.
  ``https://<account>.services.ai.azure.com/api/projects/<project>``
- ``MODEL_DEPLOYMENT_NAME`` — a chat model deployment on the project (e.g. ``gpt-4o``)
- ``FABRIC_IQ_CONNECTION_ID`` — a Fabric IQ connection id. A placeholder is
  accepted at registration time; only *Fabric* questions require a real one.

Usage::

    uv run python scripts/verify_foundry_agent.py

Exit code is 0 on success, 1 on failure, 2 on missing configuration.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# A question that the model can answer with the local compute_quota_attainment
# tool, so the round-trip does not depend on a live Fabric connection.
_LOCAL_TOOL_QUESTION = (
    "Compute quota attainment from these figures and summarize the risk rating. "
    "annual_target = 1000000, ytd_actual = 600000, open_pipeline = 500000, "
    "months_elapsed = 6, days_elapsed = 180. "
    "Use the compute_quota_attainment tool; do not query the sales database."
)


def main() -> int:
    """Register the agent, confirm it is listed, and run one Playground-style query."""
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    from src.orchestrator.config import ConfigurationError, OrchestratorConfig
    from src.orchestrator.foundry_agent import _AGENT_NAME, _get_or_create_agent, run_query

    try:
        config = OrchestratorConfig.from_env()
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


if __name__ == "__main__":
    raise SystemExit(main())
