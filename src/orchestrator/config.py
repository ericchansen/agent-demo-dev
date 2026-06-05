"""Orchestrator configuration.

Required environment variables:
- FOUNDRY_PROJECT_ENDPOINT
- FABRIC_IQ_CONNECTION_ID
- MODEL_DEPLOYMENT_NAME

Optional environment variables:
- WORK_IQ_CONNECTION_ID
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when required environment variables are missing."""


@dataclass(frozen=True)
class OrchestratorConfig:
    """Configuration for the Azure AI Foundry orchestrator."""

    foundry_project_endpoint: str
    model_deployment_name: str
    fabric_iq_connection_id: str
    workiq_connection_id: str | None = None

    @classmethod
    def from_env(cls) -> OrchestratorConfig:
        """Build config from environment variables."""
        load_dotenv()

        missing: list[str] = []
        endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
        if not endpoint:
            missing.append("FOUNDRY_PROJECT_ENDPOINT")

        fabric_iq = os.environ.get("FABRIC_IQ_CONNECTION_ID")
        if not fabric_iq:
            missing.append("FABRIC_IQ_CONNECTION_ID")

        model = os.environ.get("MODEL_DEPLOYMENT_NAME")
        if not model:
            missing.append("MODEL_DEPLOYMENT_NAME")

        if missing:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Copy .env.example to .env and fill in the values. "
                f"See docs/setup-guide.md for details."
            )

        assert endpoint is not None
        assert fabric_iq is not None
        assert model is not None

        return cls(
            foundry_project_endpoint=endpoint,
            model_deployment_name=model,
            fabric_iq_connection_id=fabric_iq,
            workiq_connection_id=os.environ.get("WORK_IQ_CONNECTION_ID"),
        )
