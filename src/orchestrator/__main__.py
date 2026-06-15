"""CLI entry point for testing the orchestrator locally."""

from __future__ import annotations

import json
import sys

from src.orchestrator.databricks_genie import databricks_genie_query_func
from src.orchestrator.foundry_agent import run_query


def _is_direct_databricks_smoke(question: str) -> bool:
    lowered = question.lower()
    return "databricks genie" in lowered or lowered.startswith("databricks:")


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Ask: ")
    if _is_direct_databricks_smoke(question):
        result = databricks_genie_query_func({"question": question.removeprefix("databricks:").strip()})
        print(json.dumps(result, indent=2, default=str))
        raise SystemExit(0 if result.get("status") == "ok" else 2)
    print(run_query(question))
