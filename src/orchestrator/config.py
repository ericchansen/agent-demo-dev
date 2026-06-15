"""Orchestrator configuration.

Required environment variables:
- FOUNDRY_PROJECT_ENDPOINT
- MODEL_DEPLOYMENT_NAME

Optional environment variables:
- FABRIC_IQ_CONNECTION_ID (when unset, the agent uses a demo-safe fabric_query fallback)
- DATABRICKS_WORKSPACE_URL / DATABRICKS_HOST
- DATABRICKS_GENIE_SPACE_ID
- DATABRICKS_GENIE_WAREHOUSE_ID / DATABRICKS_WAREHOUSE_ID
- WORK_IQ_CONNECTION_ID
- MARKET_DATA_CONNECTION_ID
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
    fabric_iq_connection_id: str | None = None
    databricks_workspace_url: str | None = None
    databricks_genie_space_id: str | None = None
    databricks_warehouse_id: str | None = None
    workiq_connection_id: str | None = None
    market_data_connection_id: str | None = None

    @classmethod
    def from_env(cls) -> OrchestratorConfig:
        """Build config from environment variables."""
        load_dotenv()

        missing: list[str] = []
        endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
        if not endpoint:
            missing.append("FOUNDRY_PROJECT_ENDPOINT")

        model = os.environ.get("MODEL_DEPLOYMENT_NAME")
        if not model:
            missing.append("MODEL_DEPLOYMENT_NAME")

        if missing:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Create a .env file in the project root and set the missing values. "
                f"See docs/setup-guide.md for details."
            )

        assert endpoint is not None
        assert model is not None

        return cls(
            foundry_project_endpoint=endpoint,
            model_deployment_name=model,
            fabric_iq_connection_id=os.environ.get("FABRIC_IQ_CONNECTION_ID"),
            databricks_workspace_url=os.environ.get("DATABRICKS_WORKSPACE_URL") or os.environ.get("DATABRICKS_HOST"),
            databricks_genie_space_id=os.environ.get("DATABRICKS_GENIE_SPACE_ID"),
            databricks_warehouse_id=os.environ.get("DATABRICKS_GENIE_WAREHOUSE_ID")
            or os.environ.get("DATABRICKS_WAREHOUSE_ID"),
            workiq_connection_id=os.environ.get("WORK_IQ_CONNECTION_ID"),
            market_data_connection_id=os.environ.get("MARKET_DATA_CONNECTION_ID"),
        )
