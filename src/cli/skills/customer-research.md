---
name: Research Customer
description: >
  Research a customer using the Researcher Agent. Returns recent news,
  earnings data, strategy insights, and key metrics.
---

# Research Customer

## What this skill does

Calls the **Researcher Agent** (`researcher-agent` MCP server) to search the
open web for intelligence about a specific company. Returns a structured
summary with recent articles, key financial metrics, and strategic insights.

## How it works

1. The skill calls the `research_company` tool on the `researcher-agent` MCP
   server with the customer name and optional focus areas.
2. The agent searches the web (via Bing or Tavily, depending on your
   `SEARCH_PROVIDER` env var) and returns:
   - **Summary** — a concise overview of the company's current position.
   - **Articles** — recent news with title, URL, date, and snippet.
   - **Key Metrics** — revenue growth, market cap, headcount, etc.

## Example invocations

```
Research Tailspin Toys — focus on recent news and expansion
```

```
Research Contoso Ltd with a focus on earnings and strategy
```

```
What's the latest news on Adventure Works?
```

## Focus areas

You can optionally specify focus areas to refine the search:

| Focus area   | What it emphasizes                        |
|-------------|-------------------------------------------|
| `news`      | Recent press coverage and announcements    |
| `earnings`  | Financial results and revenue metrics      |
| `strategy`  | Business strategy and competitive moves    |
| `expansion` | New markets, offices, and partnerships     |

## Prerequisites

- `researcher-agent` MCP server available
- `SEARCH_PROVIDER` env var set to `bing`, `tavily`, or `mock` (default: `mock`)
- `SEARCH_API_KEY` env var set if using a live search provider
