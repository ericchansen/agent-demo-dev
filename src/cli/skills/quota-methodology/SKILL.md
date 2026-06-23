---
name: quota-methodology
version: 1.0.0
description: >-
  Versioned quota-estimation methodology for sales customers. Encodes the exact,
  deterministic growth-rate model the quota estimator implements so the same logic can be reused
  across the Copilot CLI, a Foundry agent system prompt, or a Databricks Supervisor tool.
owner: agent-demo-dev
last_reviewed: 2026-06-15
tools:
  - sales-data            # Fabric Data Agent MCP (or Databricks Genie equivalent)
  - researcher-agent          # market-context research tool
  - workiq                    # engagement-signal tool (optional, mockable)
  - quota-estimator           # generate_quota_estimation_report
---

# Quota Estimation Methodology (v1.0.0)

This is a **versioned skill**: a single source of truth for *how* a sales (sales) quota is
estimated. The CLI skill, the Foundry agent prompt, and the Databricks Supervisor `uc_function` should all
produce the **same numbers** because they all follow the formula below. Bump `version` whenever the formula,
bounds, or scenario adjustments change, and update `last_reviewed`.

The reference implementation lives in `src/agents/quota_estimator/pipeline.py`. Keep this file in sync with it.

## Intent

Generate a fiscal-year quota recommendation per **(territory, product category)** group for one customer,
grounded in trailing sales, market research, and engagement signals, under a named scenario. Produce real
artifacts (`.xlsx`, `.html`, `.pdf`), not just inline prose.

## Inputs

| Parameter | Required | Notes |
|---|---|---|
| `customer_name` | yes | e.g. `Tailspin Toys`. |
| `sales_rows` | yes | Trailing rows with `territory`, `category`, `order_date`, `revenue`, `quantity`. |
| `research_data` | no | Market context; a `growth_rate` / `key_metrics.*` hint feeds the market adjustment. |
| `workiq_activity` | no | Engagement score + activity count; mock when no credentials. |
| `scenario` | no | One of `conservative`, `base` (default), `aggressive`. |
| `data_source` | no | `fabric` or `databricks`; selects the citation/query surface only. |

## Methodology (the formula)

For each `(territory, category)` group:

1. `trailing_revenue` = sum of `revenue` in the group.
2. `historical_growth_rate` = bounded trailing trend: split the rows at their date midpoint, compute
   `(recent_revenue - previous_revenue) / previous_revenue`, then **clamp to `[-0.20, 0.30]`**. With fewer
   than two rows or a single date the trend is `0.0`. If `previous_revenue <= 0`, use `0.05` when there is
   recent revenue, else `0.0`.
3. `market_adjustment` = `clamp(growth_rate_hint / 4, -0.03, 0.05)` (`0.0` when no hint).
4. `engagement_adjustment` = `clamp(score_adjustment + volume_adjustment, -0.03, 0.05)` where
   `score_adjustment` is `very high +0.04 / high +0.03 / medium / moderate +0.01 / low -0.02 / none -0.03`
   (unknown `0.0`) and `volume_adjustment` = `min(activity_count, 6) * 0.002`.
5. `scenario_adjustment` = `conservative -0.03 / base 0.0 / aggressive +0.03`.
6. **`recommended_growth_rate`** =
   `clamp(0.04 + 0.5 * historical_growth_rate + market_adjustment + engagement_adjustment + scenario_adjustment, -0.05, 0.25)`.
7. **`recommended_quota`** = `trailing_revenue * (1 + recommended_growth_rate)`.

The `0.04` base, the `0.5` trend weight, every clamp bound, and the scenario/engagement tables are the
**contract**. Do not invent alternative numbers — that is the whole point of versioning this skill.

## Steps

1. **Query sales** via `sales-data` (Fabric Data Agent MCP) — or the Databricks Genie equivalent when the
   customer is on the Databricks path. Return at least territory, category, order date, revenue, quantity.
2. **Gather market context** via `researcher-agent.research_company`. If live search is unavailable, accept the
   mock response and say so.
3. **Gather engagement** via the configured WorkIQ tool, or synthesize realistic activity with an engagement
   score. Never call real WorkIQ APIs without credentials.
4. **Generate artifacts** by calling `quota-estimator.generate_quota_estimation_report` with `customer_name`,
   `sales_rows`, `research_data`, `workiq_activity`, `scenario`, and `formats: ["xlsx", "html", "pdf"]`.
5. **Return** an executive summary, the chosen scenario, the total recommended quota, and the artifact paths.

## Output contract

Per group, surface `trailing_revenue`, `recommended_growth_rate`, `recommended_quota`, and a one-line rationale
of the form:

```
<territory> / <category>: trend <h>%, market adjustment <m>%, engagement adjustment <e>%, <scenario> scenario adjustment <s>%.
```

Always include the data-source citation, research citations, and a WorkIQ context line so the recommendation is
auditable.

## Scenario selection hint

Infer `scenario` from intent: "stretch" / "upside" maps to `aggressive`; "downside" / "floor" maps to
`conservative`; otherwise `base`.

## Changelog

- **1.0.0** (2026-06-15) — Initial versioned methodology extracted from `quota_estimator/pipeline.py`.
