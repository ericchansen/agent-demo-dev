"""Unit tests for the markdown external-link validator."""

from __future__ import annotations

from scripts.validate_links import extract_public_urls, should_validate


def test_extract_public_urls_ignores_code_fences_and_templates() -> None:
    markdown = """
Public: [Docs](https://learn.microsoft.com/en-us/azure/foundry/)

```dotenv
FOUNDRY_PROJECT_ENDPOINT=https://fabricagentaidev2026.services.ai.azure.com/api/projects/fsa-foundry-project-dev
FABRIC_MCP_URL=https://api.fabric.microsoft.com/v1/mcp/workspaces/{workspace-id}
```
"""

    assert extract_public_urls(markdown) == {"https://learn.microsoft.com/en-us/azure/foundry/"}


def test_should_validate_skips_non_public_examples() -> None:
    assert not should_validate("http://127.0.0.1:8080/healthz")
    assert not should_validate("https://example.com/research")
    assert not should_validate("https://your-endpoint.openai.azure.com/")
    assert not should_validate(
        "https://fabricagentaidev2026.services.ai.azure.com/api/projects/fsa-foundry-project-dev"
    )


def test_should_validate_public_docs_links() -> None:
    assert should_validate("https://learn.microsoft.com/en-us/azure/databricks/genie/conversation-api")
    assert should_validate("https://github.com/ericchansen/agent-demo-dev")
