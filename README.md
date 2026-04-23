# Fabric Sales Agent Accelerator

An open-source reference implementation showing how to combine **Microsoft Fabric Data Agent** with agentic AI workflows — a Researcher Agent (web), a SharePoint Agent (internal docs), and a Report Generator — surfaced through **multiple architecture options**.

> **Choose Your Architecture:** This repo demonstrates four consumption surfaces — pick the one that fits your team.

## What It Does

A sales user asks a natural language question like *"Prepare an account plan for Tailspin Toys"* and the system:

1. **Queries pipeline data** from Fabric OneLake via the Fabric Data Agent
2. **Researches the customer** on the open web (news, earnings, strategy)
3. **Pulls internal context** from SharePoint (prior proposals, playbooks)
4. **Generates a deliverable** (DOCX or PPTX) from templates with full source citations

## Architecture Options

| Surface | Audience | Effort | Capabilities |
|---------|----------|--------|-------------|
| **GitHub Copilot (VS Code / CLI)** | Developers, power users | MCP config + skills | Full multi-agent workflow |
| **M365 Copilot (Direct)** | Business users | Zero code | Fabric data queries only |
| **Copilot Studio** | Business users | Low-code | Multi-source with connectors |
| **Azure AI Foundry** | Pro developers | Python SDK | Full orchestration + M365 publish |

See [docs/surfaces/README.md](docs/surfaces/README.md) for a detailed comparison.

## Quick Start

```bash
# 1. Deploy infrastructure
make infra-deploy

# 2. Load Wide World Importers sample data into Fabric
make load-data

# 3. Start sub-agents and run the demo
make demo
```

## Dataset

Uses **Wide World Importers** — Microsoft's sample database for a wholesale novelty goods distributor. No customer-specific data. See [demo/](demo/) for details.

## Documentation

- [Architecture Overview](docs/architecture.md)
- [Choose Your Architecture](docs/surfaces/README.md)
- [Security Model](docs/security-model.md)
- [Setup Guide](docs/setup-guide.md)
- [Cost Model](docs/costs.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
