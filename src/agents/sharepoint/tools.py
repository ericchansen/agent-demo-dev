"""SharePoint document retrieval tools — mock and Graph API backends."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock data (Wide World Importers themed)
# ---------------------------------------------------------------------------

_MOCK_DOCUMENTS: list[dict[str, Any]] = [
    {
        "name": "Account_Plan_Tailspin_Toys.docx",
        "url": "https://contoso.sharepoint.com/sites/sales/Shared Documents/Account_Plan_Tailspin_Toys.docx",
        "excerpt": "FY25 account plan for Tailspin Toys — $2.4M pipeline with expansion into novelty goods.",
        "last_modified": "2025-06-15T14:30:00Z",
    },
    {
        "name": "QBR_Q4_2025.pptx",
        "url": "https://contoso.sharepoint.com/sites/sales/Shared Documents/QBR_Q4_2025.pptx",
        "excerpt": "Quarterly business review — Wide World Importers wholesale performance and regional trends.",
        "last_modified": "2025-07-01T09:00:00Z",
    },
    {
        "name": "Sales_Playbook.md",
        "url": "https://contoso.sharepoint.com/sites/sales/Shared Documents/Sales_Playbook.md",
        "excerpt": "Sales playbook for novelty goods — discovery questions, objection handling, and ROI frameworks.",
        "last_modified": "2025-05-20T11:15:00Z",
    },
]

_MOCK_CONTENT: dict[str, Any] = {
    "name": "Account_Plan_Tailspin_Toys.docx",
    "content_text": (
        "# Account Plan — Tailspin Toys\n\n"
        "## Executive Summary\n"
        "Tailspin Toys is a strategic account in the novelty goods vertical with a $2.4M pipeline.\n\n"
        "## Key Contacts\n"
        "- VP of Procurement: Jordan Ellis\n"
        "- CTO: Morgan Blake\n\n"
        "## Next Steps\n"
        "1. Schedule executive briefing for Q3.\n"
        "2. Deliver POC results by August 15.\n"
    ),
    "url": "https://contoso.sharepoint.com/sites/sales/Shared Documents/Account_Plan_Tailspin_Toys.docx",
    "size": 24_576,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_mode() -> str:
    return os.environ.get("SHAREPOINT_MODE", "mock").lower()


async def _get_graph_token() -> str:
    """Acquire a Microsoft Graph access token via azure-identity."""
    from azure.identity.aio import DefaultAzureCredential  # noqa: PLC0415

    credential = DefaultAzureCredential()
    try:
        token = await credential.get_token("https://graph.microsoft.com/.default")
        return token.token
    finally:
        await credential.close()


async def _graph_request(method: str, url: str, *, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make an authenticated request to Microsoft Graph."""
    import aiohttp  # noqa: PLC0415

    token = await _get_graph_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        if method.upper() == "POST":
            async with session.post(url, headers=headers, json=json_body) as resp:
                resp.raise_for_status()
                return await resp.json()  # type: ignore[no-any-return]
        else:
            async with session.get(url, headers=headers) as resp:
                resp.raise_for_status()
                # Content download returns bytes; wrap in a dict for consistency
                if "content" in url and resp.content_type != "application/json":
                    raw = await resp.read()
                    return {"_raw_bytes": raw, "_content_type": resp.content_type}
                return await resp.json()  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Public tools
# ---------------------------------------------------------------------------

async def search_documents(query: str, site_id: str | None = None) -> list[dict[str, Any]]:
    """Search SharePoint for documents matching *query*.

    Returns a list of ``{name, url, excerpt, last_modified}`` dicts.
    """
    mode = _get_mode()

    if mode == "mock":
        query_lower = query.lower()
        results = [
            doc for doc in _MOCK_DOCUMENTS
            if query_lower in doc["name"].lower() or query_lower in doc["excerpt"].lower()
        ]
        return results if results else []

    # --- Graph API mode ---
    search_url = "https://graph.microsoft.com/v1.0/search/query"
    body: dict[str, Any] = {
        "requests": [
            {
                "entityTypes": ["driveItem"],
                "query": {"queryString": query},
                "from": 0,
                "size": 25,
            }
        ]
    }
    if site_id:
        body["requests"][0]["region"] = site_id  # scoping hint

    try:
        data = await _graph_request("POST", search_url, json_body=body)
    except Exception:
        logger.exception("Graph search request failed")
        raise

    hits: list[dict[str, Any]] = []
    for response_value in data.get("value", []):
        for hit_container in response_value.get("hitsContainers", []):
            for hit in hit_container.get("hits", []):
                resource = hit.get("resource", {})
                hits.append({
                    "name": resource.get("name", ""),
                    "url": resource.get("webUrl", ""),
                    "excerpt": hit.get("summary", ""),
                    "last_modified": resource.get("lastModifiedDateTime", ""),
                })
    return hits


async def get_document_content(drive_id: str, item_id: str) -> dict[str, Any]:
    """Retrieve the content of a specific document by *drive_id* and *item_id*.

    Returns ``{name, content_text, url, size}``.
    """
    mode = _get_mode()

    if mode == "mock":
        return dict(_MOCK_CONTENT)

    # --- Graph API mode ---
    metadata_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}"
    content_url = f"{metadata_url}/content"

    try:
        metadata = await _graph_request("GET", metadata_url)
        content_resp = await _graph_request("GET", content_url)
    except Exception:
        logger.exception("Graph content request failed")
        raise

    raw_bytes: bytes = content_resp.get("_raw_bytes", b"")
    content_type: str = content_resp.get("_content_type", "")

    # Best-effort text extraction
    if "text" in content_type or content_type == "application/json":
        content_text = raw_bytes.decode("utf-8", errors="replace")
    elif "wordprocessingml" in content_type:
        content_text = _extract_docx_text(raw_bytes)
    else:
        content_text = f"[Binary content — {len(raw_bytes)} bytes, type={content_type}]"

    return {
        "name": metadata.get("name", ""),
        "content_text": content_text,
        "url": metadata.get("webUrl", ""),
        "size": metadata.get("size", len(raw_bytes)),
    }


def _extract_docx_text(raw: bytes) -> str:
    """Extract plain text from an in-memory DOCX file."""
    import io  # noqa: PLC0415

    from docx import Document  # noqa: PLC0415

    doc = Document(io.BytesIO(raw))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
