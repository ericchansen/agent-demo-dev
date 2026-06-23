"""Single source of truth for agent tool JSON schemas.

Both the Foundry orchestrator (``foundry_agent``) and the hosted/local runtime
(``tool_runtime``) advertise the same function tools to their respective model
surfaces. Defining the parameter schemas here keeps the two surfaces from
drifting apart -- a mismatch would mean the Copilot CLI prototype and the
Foundry-hosted production agent expose subtly different tool contracts.

The canonical tool name set is exported as :data:`TOOL_NAMES`.
"""

from __future__ import annotations

from typing import Any

ACCOUNT_ACTIVITY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "customer_name": {
            "type": "string",
            "description": "Customer or prospect account name.",
        }
    },
    "required": ["customer_name"],
    "additionalProperties": False,
}

FABRIC_QUERY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {
            "type": "string",
            "description": "Natural language question about sales data.",
        }
    },
    "required": ["question"],
    "additionalProperties": False,
}

DATABRICKS_QUERY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {
            "type": "string",
            "description": "Natural language question for a Databricks Genie Space over Unity Catalog.",
        },
        "conversation_id": {
            "type": "string",
            "description": "Optional existing Genie conversation id for a follow-up question.",
        },
    },
    "required": ["question"],
    "additionalProperties": False,
}

FORECAST_QUOTA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "customer_name": {
            "type": "string",
            "description": "Customer or prospect account name.",
        },
        "scenario": {
            "type": "string",
            "enum": ["conservative", "base", "aggressive"],
            "description": "Deterministic forecast scenario applied to recommended growth (default base).",
        },
    },
    "required": ["customer_name"],
    "additionalProperties": False,
}

_QUOTA_SALES_ROW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Sales row from Fabric Data Agent or Databricks Genie / Unity Catalog.",
    "additionalProperties": True,
}

GENERATE_QUOTA_ESTIMATION_REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "customer_name": {
            "type": "string",
            "description": "Customer or prospect account name.",
        },
        "sales_rows": {
            "type": "array",
            "description": (
                "Historical sales rows with territory, order_date, revenue, and optional category/quantity. "
                "Databricks aliases such as sales_territory, orderDate, net_sales_amount, and units_sold "
                "are also accepted."
            ),
            "items": _QUOTA_SALES_ROW_SCHEMA,
        },
        "data_source": {
            "type": "string",
            "enum": ["fabric", "databricks"],
            "description": "Optional platform override used for report methodology and source citations.",
        },
        "research_data": {
            "type": "object",
            "description": "Market research payload with summary, articles, and key metrics.",
            "additionalProperties": True,
        },
        "workiq_activity": {
            "type": "object",
            "description": "WorkIQ or synthetic M365 activity signals.",
            "additionalProperties": True,
        },
        "scenario": {
            "type": "string",
            "enum": ["conservative", "base", "aggressive"],
            "description": "Deterministic forecast scenario applied to recommended growth (default base).",
        },
        "output_dir": {
            "type": "string",
            "description": "Directory where XLSX, HTML, and PDF artifacts should be written.",
        },
        "formats": {
            "type": "array",
            "description": "Artifact formats to generate.",
            "items": {"type": "string", "enum": ["xlsx", "html", "pdf"]},
        },
    },
    "required": ["customer_name", "sales_rows"],
    "additionalProperties": False,
}

_FORECAST_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "description": "Forecast category name."},
        "current_fy_revenue": {"type": "number", "description": "Current fiscal year revenue."},
        "growth_rate": {"type": "number", "description": "Projected growth rate as a decimal."},
        "projected_fy_revenue": {"type": "number", "description": "Projected fiscal year revenue."},
    },
    "required": ["category", "current_fy_revenue", "growth_rate", "projected_fy_revenue"],
    "additionalProperties": False,
}

_FORECAST_DATA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Optional quota forecast payload to render in the DOCX report.",
    "properties": {
        "current_fy_total": {"type": "number", "description": "Current fiscal year total revenue."},
        "projected_fy_total": {"type": "number", "description": "Projected fiscal year total revenue."},
        "overall_growth_rate": {"type": "number", "description": "Overall projected growth rate."},
        "methodology": {"type": "string", "description": "Short description of the forecast methodology."},
        "items": {
            "type": "array",
            "description": "Forecast line items by category.",
            "items": _FORECAST_ITEM_SCHEMA,
        },
    },
    "required": ["current_fy_total", "projected_fy_total", "overall_growth_rate", "methodology", "items"],
    "additionalProperties": False,
}

_REPORT_SECTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "deal_name": {"type": "string", "description": "Opportunity or deal name."},
        "value": {"type": "number", "description": "Opportunity value in customer currency."},
        "stage": {"type": "string", "description": "Current sales stage."},
        "close_date": {"type": "string", "description": "Expected close date."},
    },
    "required": ["deal_name", "value", "stage", "close_date"],
    "additionalProperties": False,
}

GENERATE_REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Title for the generated report."},
        "customer_name": {
            "type": "string",
            "description": "Customer or prospect account name.",
        },
        "sections": {
            "type": "array",
            "description": "Deprecated alias for pipeline_data.",
            "items": _REPORT_SECTION_SCHEMA,
        },
        "pipeline_data": {
            "type": "array",
            "description": "Pipeline rows to include in the report.",
            "items": _REPORT_SECTION_SCHEMA,
        },
        "research_data": {
            "type": "object",
            "description": "Customer research payload with summary and article metadata.",
            "additionalProperties": True,
        },
        "sharepoint_docs": {
            "type": "array",
            "description": "Referenced SharePoint documents with name, url, and excerpt.",
            "items": {"type": "object", "additionalProperties": True},
        },
        "forecast_data": {
            "anyOf": [
                _FORECAST_DATA_SCHEMA,
                {"type": "null"},
            ],
            "description": "Optional quota forecast payload to render in the DOCX report.",
        },
        "additional_context": {
            "type": "string",
            "description": "Additional notes to append to the report.",
        },
    },
    "required": ["title", "customer_name"],
    "additionalProperties": False,
}

WEB_RESEARCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query for market research, customer news, or competitive intelligence.",
        },
        "customer_name": {
            "type": "string",
            "description": "Optional customer name to contextualize results.",
        },
    },
    "required": ["query"],
    "additionalProperties": False,
}

COMPUTE_ATTAINMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "annual_target": {
            "type": "number",
            "description": "Annual quota target in dollars.",
        },
        "ytd_actual": {
            "type": "number",
            "description": "Year-to-date actual revenue in dollars.",
        },
        "open_pipeline": {
            "type": "number",
            "description": "Total value of open pipeline deals.",
        },
        "months_elapsed": {
            "type": "number",
            "description": "Number of months elapsed in current fiscal year.",
        },
        "days_elapsed": {
            "type": "number",
            "description": "Number of days elapsed in current fiscal year.",
        },
    },
    "required": ["annual_target", "ytd_actual", "open_pipeline", "months_elapsed", "days_elapsed"],
    "additionalProperties": False,
}

#: Canonical set of tool names every agent surface must expose.
TOOL_NAMES: frozenset[str] = frozenset(
    {
        "fabric_query",
        "databricks_query",
        "forecast_quota",
        "generate_quota_estimation_report",
        "generate_report",
        "web_research",
        "compute_quota_attainment",
        "get_account_activity",
    }
)

__all__ = [
    "ACCOUNT_ACTIVITY_SCHEMA",
    "COMPUTE_ATTAINMENT_SCHEMA",
    "DATABRICKS_QUERY_SCHEMA",
    "FABRIC_QUERY_SCHEMA",
    "FORECAST_QUOTA_SCHEMA",
    "GENERATE_QUOTA_ESTIMATION_REPORT_SCHEMA",
    "GENERATE_REPORT_SCHEMA",
    "TOOL_NAMES",
    "WEB_RESEARCH_SCHEMA",
]
