# Fabric Sales Agent Accelerator — Makefile
# Usage: make <target>

RG ?= fsa-demo-rg
CAPACITY_NAME ?= fsa-demo-capacity
MOCK ?= 1
PASS_RATE ?= 100
CATEGORY ?=

.PHONY: lint format format-check typecheck test test-integration test-eval recorded-proof predemo \
        infra-validate infra-deploy infra-teardown load-data load-market-data \
        configure-market-agent serve-researcher serve-sharepoint demo diagrams clean

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

format-check:
	ruff format --check src/ tests/

typecheck:
	mypy src/

test:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-eval:
	python tests/eval/run_eval.py $(if $(filter 1 true yes,$(MOCK)),--mock,) --pass-rate $(PASS_RATE) $(if $(CATEGORY),--category $(CATEGORY),)

# Recorded / offline backend E2E proof: replays non-secret Fabric- and
# Databricks-shaped fixtures through the real quota pipeline -> report path.
# Offline only; never contacts a live backend.
recorded-proof:
	python scripts/recorded_live_proof.py

predemo:
	python scripts/predemo.py

infra-validate:
	az bicep build --file infra/main.bicep

infra-deploy:
	az deployment group create \
		--resource-group $(RG) \
		--template-file infra/main.bicep \
		--parameters infra/parameters/dev.bicepparam

infra-teardown:
	@echo "To pause Fabric capacity (saves cost when not in use):"
	@echo "  az fabric capacity suspend --capacity-name $(CAPACITY_NAME) --resource-group $(RG)"

load-data:
	python demo/load-wwi-data.py

load-market-data:
	python demo/load-market-data.py

configure-market-agent:
	@echo "Usage: python demo/configure_market_agent.py --workspace-id <GUID> --agent-id <GUID> --lakehouse-id <GUID>"

serve-researcher:
	python -m src.agents.researcher.mcp_server

serve-sharepoint:
	python -m src.agents.sharepoint.mcp_server

demo:
	copilot --no-custom-instructions

diagrams:
	python docs/diagrams/generate.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .mypy_cache .pytest_cache .coverage
