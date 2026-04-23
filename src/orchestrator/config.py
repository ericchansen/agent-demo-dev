"""Orchestrator configuration — reads all settings from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class OrchestratorConfig:
    """Configuration for the Azure AI Foundry orchestrator.

    All values are sourced from environment variables — nothing is hardcoded.
    """

    # Azure AI Foundry
    foundry_project_connection: str
    model_deployment_name: str

    # Fabric
    fabric_connection_id: str

    # Search (web research)
    search_provider: str  # "bing" | "tavily" | "none"
    search_api_key: str

    # SharePoint
    sharepoint_mode: str  # "graph" | "connector" | "none"

    @classmethod
    def from_env(cls) -> OrchestratorConfig:
        """Build config from environment variables.

        Required env vars:
            FOUNDRY_PROJECT_CONNECTION  – Foundry project connection string
            FABRIC_CONNECTION_ID        – Fabric Data Agent connection ID
            MODEL_DEPLOYMENT_NAME       – Deployed model name (e.g. "gpt-4o")

        Optional env vars (default to "none" / empty):
            SEARCH_PROVIDER   – "bing", "tavily", or "none"
            SEARCH_API_KEY    – API key for the search provider
            SHAREPOINT_MODE   – "graph", "connector", or "none"
        """
        foundry_conn = os.environ.get("FOUNDRY_PROJECT_CONNECTION", "")
        if not foundry_conn:
            raise OSError(
                "FOUNDRY_PROJECT_CONNECTION is required. "
                "Set it to your Azure AI Foundry project connection string."
            )

        fabric_id = os.environ.get("FABRIC_CONNECTION_ID", "")
        if not fabric_id:
            raise OSError(
                "FABRIC_CONNECTION_ID is required. "
                "Set it to the connection ID of your Fabric Data Agent."
            )

        model_name = os.environ.get("MODEL_DEPLOYMENT_NAME", "")
        if not model_name:
            raise OSError(
                "MODEL_DEPLOYMENT_NAME is required. "
                "Set it to the name of your deployed model (e.g. 'gpt-4o')."
            )

        return cls(
            foundry_project_connection=foundry_conn,
            fabric_connection_id=fabric_id,
            model_deployment_name=model_name,
            search_provider=os.environ.get("SEARCH_PROVIDER", "none"),
            search_api_key=os.environ.get("SEARCH_API_KEY", ""),
            sharepoint_mode=os.environ.get("SHAREPOINT_MODE", "none"),
        )
