---
name: competitive-intel
description: Competitive intelligence brief combining SEC financials with live web research
---

# Competitive Intelligence Brief

You are generating a competitive intelligence brief that combines structured SEC financial data with live web research for real-time context.

## Steps

1. **Pull structured financials**: Use the `market-data` MCP server to get SEC-filed financials for the target company and its competitors. Example:
   ```
   Show revenue, net income, and total assets for Microsoft, Google, and Amazon from their most recent 10-K filings.
   ```

2. **Identify competitors**: Use the `companies` table to find companies in the same SIC industry. Example:
   ```
   What other companies share the same SIC code as MSFT?
   ```

3. **Financial comparison table**:
   | Metric | Target Co. | Competitor A | Competitor B |
   |--------|-----------|-------------|-------------|
   | Revenue | $XXM | $YYM | $ZZM |
   | Net Income | $XXM | $YYM | $ZZM |
   | Margin % | X% | Y% | Z% |
   | Total Assets | $XXM | $YYM | $ZZM |
   | YoY Growth | X% | Y% | Z% |

4. **Live research enrichment** (when available): Use the `researcher-agent` MCP server to search for recent news, earnings announcements, and strategic moves. Example queries:
   ```
   Search for recent news about Microsoft Azure revenue growth
   ```
   ```
   What are the latest analyst estimates for NVIDIA's next quarter?
   ```

   > **Note**: Live web research requires `SEARCH_PROVIDER=bing` or `SEARCH_PROVIDER=tavily` and a valid API key. When set to `mock` (default), the researcher returns sample data for Tailspin Toys.

5. **Synthesize the brief**:
   - **Company Profile**: Core business, industry position, key products
   - **Financial Snapshot**: Latest revenue, income, growth trajectory (from SEC data)
   - **Competitive Position**: How they stack up vs. industry peers (from SEC data)
   - **Recent Developments**: News, product launches, strategic shifts (from live research)
   - **Outlook**: Growth drivers, risks, analyst sentiment (from live research)

6. **Source attribution**:
   - SEC data: "Source: SEC EDGAR, [filing type], filed [date]"
   - Web research: Include URLs from the researcher agent results
   - Clearly label which insights come from audited filings vs. news/analyst reports

## Example Invocations

- "Build a competitive intel brief for Microsoft in cloud computing"
- "Compare NVIDIA vs AMD in the semiconductor market"
- "Analyze JPMorgan Chase's competitive position in banking"

## Data Sources

| Source | Type | Coverage | Requirements |
|--------|------|----------|-------------|
| `market-data` (SEC EDGAR) | Structured financials | ~50 companies, quarterly | MCP URL configured |
| `researcher-agent` (Web) | News, analysis | Real-time | `SEARCH_PROVIDER` + API key |
