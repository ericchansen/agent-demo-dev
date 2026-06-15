---
sidebar_position: 6
title: Report Generation
---

# Report Generation

One of the clearest ways an agent moves beyond "chatbot" is when it produces a real deliverable — not just text in a chat window, but a formatted document you can send to a customer or present to your manager.

This accelerator includes report generators that produce DOCX account briefs and quota-estimation XLSX, HTML,
and PDF artifacts with forecasts, charts, citations, and activity summaries.

## What the report contains

A generated QBR forecast report includes:

- **Executive summary** — key takeaways in plain language
- **Sales by category** — table and chart of revenue by product category
- **Trend analysis** — quarter-over-quarter comparisons
- **Quota forecast** — FY projections based on historical trends
- **Activity summary** — recent engagement context from WorkIQ
- **Citations** — every number traced to its source query and timestamp

## Implementation

The DOCX report generator lives in `src/agents/report_generator/`; the quota artifact generator lives in
`src/agents/quota_estimator/`. Together they use:

- **[python-docx](https://python-docx.readthedocs.io/)** — builds formatted DOCX documents
- **[matplotlib](https://matplotlib.org/)** or chart libraries — generates embedded visualizations
- **Microsoft Graph API** — uploads to OneDrive and returns a sharing link
- **openpyxl** — writes workbook tabs for Summary, Recommendations, Sales Detail, Methodology, and Assumptions

### CLI surface
In the CLI, the quota estimator writes real XLSX, HTML, and PDF files under `output/`. The DOCX account-plan
generator remains available as a separate MCP tool for Word-style briefs.

### Foundry surface
In Foundry, report generation runs as custom function tools. Quota reports return local or uploaded
XLSX/HTML/PDF artifacts; account briefs can produce DOCX and upload through Microsoft Graph when OneDrive
permissions are configured.

> 📖 [Microsoft Graph: upload files](https://learn.microsoft.com/graph/api/driveitem-put-content) · [OneDrive sharing links](https://learn.microsoft.com/graph/api/driveitem-createlink)

## Citations as a design principle

Every generated report in this accelerator includes source attribution. This isn't optional — it's what makes AI-generated reports trustworthy enough to share externally.

Each data point includes:
- The source query or semantic endpoint that produced it
- The timestamp of the query
- Whether the value is raw data or a model inference
- The data platform: Fabric Data Agent or Databricks Genie / Unity Catalog

This traceability is critical for regulated industries and builds user trust in AI-generated content.

## Further reading

- [python-docx documentation](https://python-docx.readthedocs.io/)
- [Microsoft Graph files API](https://learn.microsoft.com/graph/api/resources/driveitem)
- [Foundry function tools](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/function-calling)
