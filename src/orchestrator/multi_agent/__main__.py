"""Command entry point for the multi-agent pipeline proof of concept."""

from __future__ import annotations

import argparse
import json

from src.orchestrator.multi_agent import run_multi_agent_pipeline
from src.orchestrator.multi_agent.agent_framework_runtime import (
    resolve_multi_agent_runtime,
    run_agent_framework_pipeline,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the WWI multi-agent quota pipeline.")
    parser.add_argument("message", nargs="*", help="User request to send to the conversational agent.")
    parser.add_argument("--customer", default="Wide World Importers", help="Customer/account name.")
    parser.add_argument("--data-source", choices=["fabric", "databricks"], default="fabric")
    parser.add_argument("--scenario", choices=["conservative", "base", "aggressive"], default="base")
    parser.add_argument("--output-dir", default="output/multi-agent")
    parser.add_argument(
        "--runtime",
        choices=["deterministic", "agent-framework"],
        default=None,
        help="Runtime to use. Defaults to WWI_MULTI_AGENT_RUNTIME or deterministic.",
    )
    args = parser.parse_args()
    message = " ".join(args.message) or f"Generate a quota report for {args.customer}"
    runtime = resolve_multi_agent_runtime(args.runtime)
    result = (
        run_agent_framework_pipeline(message, customer_name=args.customer, data_source=args.data_source)
        if runtime == "agent-framework"
        else run_multi_agent_pipeline(
            message,
            customer_name=args.customer,
            data_source=args.data_source,
            scenario=args.scenario,
            output_dir=args.output_dir,
        )
    )
    print(
        json.dumps(
            result,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
