# Contributing

## Getting Started

### Prerequisites

- Python 3.11+
- Azure CLI with Bicep (`az bicep install`)
- A Microsoft Fabric workspace (F2+ capacity)
- Access to a Fabric SQL analytics endpoint

### Setup

```bash
git clone <this-repo>
cd fabric-sales-agent-accelerator-scaffold
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env  # fill in your connection strings
```

## Development Workflow

1. **Branch** — create a feature branch from `main`: `feat/description`, `fix/description`, etc.
2. **Code** — make changes in `src/`, add tests in `tests/`.
3. **Test** — run `make lint`, `make typecheck`, and `make test` before committing.
4. **Commit** — use conventional commit messages (see below).
5. **PR** — open a pull request against `main`.

## Code Style

We use **ruff** for linting and formatting, **mypy** for type checking.

| Setting      | Value |
|-------------|-------|
| Line length | 120   |
| Target      | py311 |
| Formatter   | ruff  |
| Type checker| mypy  |

```bash
make lint          # check for issues
make format        # auto-format
make format-check  # CI-friendly format check
make typecheck     # static type analysis
```

All code must pass `make lint`, `make format-check`, and `make typecheck` before merge.

## Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

**Types:**

| Type     | When to use                                |
|----------|--------------------------------------------|
| `feat`   | New feature or capability                  |
| `fix`    | Bug fix                                    |
| `docs`   | Documentation only                         |
| `infra`  | Bicep templates, CI/CD, deployment scripts |
| `test`   | Adding or updating tests                   |
| `chore`  | Dependency updates, config, tooling        |

**Scope** is optional but encouraged: `researcher`, `sharepoint`, `orchestrator`, `fabric`, `infra`.

Examples:
```
feat(researcher): add MCP tool for customer lookup
fix(orchestrator): handle empty agent response gracefully
infra: add Fabric capacity Bicep module
```

## Testing

```bash
make test              # unit tests (required to pass)
make test-integration  # integration tests (recommended)
make test-eval         # LLM evaluation suite
```

- **Unit tests** (`tests/unit/`) — required for all PRs. Mock external services.
- **Integration tests** (`tests/integration/`) — run against real Fabric endpoints. Recommended before merge.
- **Eval tests** (`tests/eval/`) — LLM output quality checks. Run manually for agent changes.

Place tests alongside the module they cover: `tests/unit/agents/test_researcher.py` for `src/agents/researcher/`.

## Infrastructure as Code

All Azure resources live in `infra/` as Bicep templates.

- **`main.bicep`** — top-level orchestration; references modules.
- **`modules/`** — one `.bicep` file per resource (e.g., `fabric-capacity.bicep`, `key-vault.bicep`).
- **`parameters/`** — environment-specific `.bicepparam` files (`dev.bicepparam`, `prod.bicepparam`).

Conventions:
- Use `camelCase` for parameter and variable names.
- Every module must accept `location` and `tags` parameters.
- Validate before committing: `make infra-validate`.

## Pull Requests

### Checklist

- [ ] `make lint` passes
- [ ] `make format-check` passes
- [ ] `make typecheck` passes
- [ ] `make test` passes
- [ ] New/changed code has unit tests
- [ ] Bicep changes validated with `make infra-validate`
- [ ] PR description explains *what* and *why*

### Review Process

- All PRs require one approval before merge.
- Use **Rebase and merge** — keep history linear.
- Resolve all review comments before merging.
