---
sidebar_position: 6
title: Report Generation
---

# Report Generation

One of the clearest ways an agent moves beyond "chatbot" is when it produces a real deliverable — not just text in a chat window, but a formatted document you can send to a customer or present to your manager.

This accelerator includes a report generator that produces DOCX files with quota forecasts, charts, citations, and activity summaries.

## What the report contains

A generated QBR forecast report includes:

- **Executive summary** — key takeaways in plain language
- **Sales by category** — table and chart of revenue by product category
- **Trend analysis** — quarter-over-quarter comparisons
- **Quota forecast** — FY projections based on historical trends
- **Activity summary** — recent engagement context from WorkIQ
- **Citations** — every number traced to its source query and timestamp

## Implementation

The report generator lives in `src/agents/report_generator/` and uses:

- **[python-docx](https://python-docx.readthedocs.io/)** — builds formatted DOCX documents
- **[matplotlib](https://matplotlib.org/)** or chart libraries — generates embedded visualizations
- **Microsoft Graph API** — uploads to OneDrive and returns a sharing link

### CLI surface
In the CLI, reports are rendered as inline markdown (tables, projections, trend indicators). The CLI doesn't produce DOCX files — it's a developer prototype surface.

### Foundry surface
In Foundry, the report generator runs as a custom function tool. It produces a DOCX, uploads it to the user's OneDrive via Graph API, and returns a download link in the chat.

> 📖 [Microsoft Graph: upload files](https://learn.microsoft.com/graph/api/driveitem-put-content) · [OneDrive sharing links](https://learn.microsoft.com/graph/api/driveitem-createlink)

## Citations as a design principle

Every generated report in this accelerator includes source attribution. This isn't optional — it's what makes AI-generated reports trustworthy enough to share externally.

Each data point includes:
- The SQL query that produced it
- The timestamp of the query
- Whether the value is raw data or a model inference

This traceability is critical for regulated industries and builds user trust in AI-generated content.

## Further reading

- [python-docx documentation](https://python-docx.readthedocs.io/)
- [Microsoft Graph files API](https://learn.microsoft.com/graph/api/resources/driveitem)
- [Foundry function tools](https://learn.microsoft.com/azure/ai-foundry/how-to/agents/agents-function-calling)
