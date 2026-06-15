"""Working multi-agent pipeline proof of concept for the workshop."""

from src.orchestrator.multi_agent.pipeline import (
    AgentRegistration,
    MultiAgentPipeline,
    MultiAgentPipelineResult,
    run_multi_agent_pipeline,
)

__all__ = [
    "AgentRegistration",
    "MultiAgentPipeline",
    "MultiAgentPipelineResult",
    "run_multi_agent_pipeline",
]
