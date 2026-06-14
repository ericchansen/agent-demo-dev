# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Unreleased

### Added
- Initial project scaffolding
- Directory structure for sub-agents, orchestrator, CLI skills, IaC, docs, and demos
- Wide World Importers as demo dataset
- Fabric Data Agent configuration templates
- CI/CD with GitHub Actions
- Bicep IaC for Azure infrastructure
- Quota estimation pipeline (`src/agents/quota_estimator/`) producing real XLSX, HTML, and PDF artifacts from
  Fabric sales rows, market research context, and WorkIQ activity, exposed as a `quota-estimator` MCP server,
  a Copilot CLI `quota-forecast` skill, and a Foundry `generate_quota_estimation_report` function tool
- Deterministic quota scenarios (`conservative`, `base`, `aggressive`) wired through the pipeline API, MCP and
  Foundry schemas, and CLI skill, with strictly increasing quota totals
- Excel **Assumptions** worksheet detailing the baseline trend, market, engagement, and scenario adjustments behind
  each recommendation, plus an inline base64 chart embedded in the HTML report
- Synthetic WorkIQ fallback and injectable `as_of` / `generated_at` dates so demos stay current while tests remain
  deterministic
- `researcher-agent` and `sharepoint-agent` entries aligned across `.github/mcp.json` and `.vscode/mcp.json`

### Changed
- Quota artifact file names now include the selected scenario (`*_<scenario>_quota_estimate.*`)
