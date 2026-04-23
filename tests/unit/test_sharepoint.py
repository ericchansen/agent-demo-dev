"""Unit tests for the SharePoint agent tools (mock mode)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from src.agents.sharepoint.tools import get_document_content, search_documents


@pytest.fixture(autouse=True)
def _mock_mode():
    """Ensure all tests run in mock mode."""
    with patch.dict(os.environ, {"SHAREPOINT_MODE": "mock"}):
        yield


class TestSearchDocuments:
    """Tests for search_documents in mock mode."""

    async def test_search_returns_list(self) -> None:
        results = await search_documents("account")
        assert isinstance(results, list)
        assert len(results) > 0

    async def test_search_finds_account_plan(self) -> None:
        results = await search_documents("tailspin")
        names = [r["name"] for r in results]
        assert "Account_Plan_Tailspin_Toys.docx" in names

    async def test_search_finds_qbr(self) -> None:
        results = await search_documents("quarterly")
        names = [r["name"] for r in results]
        assert "QBR_Q4_2025.pptx" in names

    async def test_search_finds_playbook(self) -> None:
        results = await search_documents("playbook")
        names = [r["name"] for r in results]
        assert "Sales_Playbook.md" in names

    async def test_search_result_has_required_keys(self) -> None:
        results = await search_documents("account")
        for doc in results:
            assert "name" in doc
            assert "url" in doc
            assert "excerpt" in doc
            assert "last_modified" in doc

    async def test_search_empty_results(self) -> None:
        results = await search_documents("nonexistent-query-xyz-12345")
        assert results == []

    async def test_search_case_insensitive(self) -> None:
        results_lower = await search_documents("tailspin")
        results_upper = await search_documents("TAILSPIN")
        assert len(results_lower) == len(results_upper)


class TestGetDocumentContent:
    """Tests for get_document_content in mock mode."""

    async def test_returns_dict(self) -> None:
        result = await get_document_content(drive_id="mock-drive", item_id="mock-item")
        assert isinstance(result, dict)

    async def test_has_required_keys(self) -> None:
        result = await get_document_content(drive_id="mock-drive", item_id="mock-item")
        assert "name" in result
        assert "content_text" in result
        assert "url" in result
        assert "size" in result

    async def test_content_is_nonempty(self) -> None:
        result = await get_document_content(drive_id="mock-drive", item_id="mock-item")
        assert len(result["content_text"]) > 0

    async def test_returns_expected_doc(self) -> None:
        result = await get_document_content(drive_id="mock-drive", item_id="mock-item")
        assert "Tailspin Toys" in result["content_text"]
