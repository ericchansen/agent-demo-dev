# Sales Agent Demo — Makefile
# Usage: make <target>

RG ?= fsa-demo-rg
CAPACITY_NAME ?= fsa-demo-capacity
MOCK ?= 1
PASS_RATE ?= 100
CATEGORY ?=

.PHONY: lint format format-check typecheck test test-integration test-eval recorded-proof predemo \
        infra-validate infra-deploy infra-teardown load-data load-market-data \
        configure-market-agent demo diagrams clean

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
	python demo/load-sample-data.py

# Pull real SEC EDGAR financials for ~50 US public companies into data/sec-edgar/*.csv.
# Requires a descriptive SEC User-Agent (or set SEC_USER_AGENT).
load-market-data:
	python scripts/load_sec_edgar.py --user-agent "$(SEC_USER_AGENT)"

configure-market-agent:
	@echo "Usage: python demo/configure_market_agent.py --workspace-id <GUID> --agent-id <GUID> --lakehouse-id <GUID>"

demo:
	@echo "=== Sales Agent Demo — Full Demo ==="
	@echo ""
	@echo "1. Load sales sample data:   make load-data"
	@echo "2. Load real market data:    make load-market-data SEC_USER_AGENT='Your Name you@example.com'"
	@echo "3. Upload the CSVs to your Fabric Lakehouse and build the Data Agent (docs/setup-guide.md)."
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
