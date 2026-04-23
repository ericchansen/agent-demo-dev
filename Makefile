# Fabric Sales Agent Accelerator — Makefile
# Usage: make <target>

RG ?= fsa-demo-rg
CAPACITY_NAME ?= fsa-demo-capacity

.PHONY: lint format format-check typecheck test test-integration test-eval \
        infra-validate infra-deploy infra-teardown load-data \
        serve-researcher serve-sharepoint demo diagrams clean

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
	python tests/eval/run_eval.py

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

serve-researcher:
	python -m src.agents.researcher.mcp_server

serve-sharepoint:
	python -m src.agents.sharepoint.mcp_server

demo:
	@echo "=== Fabric Sales Agent Accelerator — Full Demo ==="
	@echo ""
	@echo "1. Load sample data:        make load-data"
	@echo "2. Start researcher agent:   make serve-researcher  (in terminal 1)"
	@echo "3. Start SharePoint agent:   make serve-sharepoint  (in terminal 2)"
	@echo "4. Open the Fabric Data Agent in your browser and start chatting."
	@echo ""
	@echo "Prerequisites:"
	@echo "  - Fabric workspace provisioned (make infra-deploy)"
	@echo "  - .env configured with connection strings"
	@echo "  - Python venv activated with dependencies installed"

diagrams:
	python docs/diagrams/generate.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .mypy_cache .pytest_cache .coverage
