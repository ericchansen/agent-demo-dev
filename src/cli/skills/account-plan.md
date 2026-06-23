---
name: Generate Account Plan
description: >
  Generate a comprehensive account plan for a sales customer,
  combining pipeline data from Fabric, web research, and internal SharePoint
  documents into a DOCX report with full citations.
---

# Generate Account Plan

## What this skill does

Produces a ready-to-share **account plan document** (DOCX) for a given customer
by orchestrating three data sources and the report generator:

1. **Pipeline data** — query the Fabric Data Agent (`sales-data` MCP) for
   the customer's open deals, values, stages, expected close dates, and
   territory breakdown.
2. **Web research** — call the Researcher Agent (`researcher-agent` MCP) to
   gather recent news articles, earnings data, strategy insights, and key
   metrics about the customer.
3. **Internal documents** — call the SharePoint Agent (`sharepoint-agent` MCP)
   to find prior proposals, existing account plans, QBR decks, and sales
   playbooks related to the customer.
4. **Report generation** — combine all collected data and generate a structured
   DOCX account plan with an executive summary, pipeline overview, customer
   intelligence section, internal references, and full citations for every
   source.
5. **Save** — write the finished document to the user's preferred location
   (defaults to the current directory).

## Steps (detailed)

### Step 1 — Query the sales pipeline

Use the `sales-data` MCP server to retrieve pipeline data:

```
Ask sales-data:
  "Show all open deals for <customer>, including deal name, value, stage,
   expected close date, and assigned territory."
```

Capture: deal list, total pipeline value, weighted value, stage distribution.

### Step 2 — Research the customer

Use the `researcher-agent` MCP server:

```
Call research_company:
  company_name: "<customer>"
  focus_areas: "news, earnings, strategy, expansion"
```

Capture: summary, recent articles (title, URL, date, snippet), key metrics.

### Step 3 — Find internal documents

Use the `sharepoint-agent` MCP server:

```
Call search_documents:
  query: "<customer> account plan OR proposal OR playbook"
```

Capture: document names, URLs, excerpts, last-modified dates.

### Step 4 — Generate the account plan

Combine all data into a structured DOCX using the report generator:

- **Executive Summary** — 2-3 sentence overview of the customer, pipeline
  posture, and strategic outlook.
- **Pipeline Overview** — table of open deals with value, stage, and close date.
- **Customer Intelligence** — recent news, earnings, strategic moves, key
  metrics. Each item cited with source URL and date.
- **Internal References** — list of related SharePoint documents with links.
- **Recommended Next Steps** — data-driven suggestions based on pipeline stage
  and research findings.
- **Citations** — full list of all sources used.

### Step 5 — Save output

Save the DOCX to the user's preferred location. Default filename:
`Account_Plan_<Customer>_<YYYY-MM-DD>.docx`

## Example invocation

```
Generate an account plan for Tailspin Toys
```

```
Create an account plan for Contoso Ltd — focus on their APAC expansion
```

## Prerequisites

- `sales-data` MCP server configured with a valid Fabric Data Agent URL
- `researcher-agent` MCP server available (requires `SEARCH_PROVIDER` env var)
- `sharepoint-agent` MCP server available (set `SHAREPOINT_MODE=mock` for demo)
- Python 3.11+ with project dependencies installed
