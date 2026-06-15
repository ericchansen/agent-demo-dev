"""Command entry point for the multi-agent pipeline proof of concept."""

from __future__ import annotations

import argparse
import json

from src.orchestrator.multi_agent import run_multi_agent_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the WWI multi-agent quota pipeline.")
    parser.add_argument("message", nargs="*", help="User request to send to the conversational agent.")
    parser.add_argument("--customer", default="Wide World Importers", help="Customer/account name.")
    parser.add_argument("--data-source", choices=["fabric", "databricks"], default="fabric")
    parser.add_argument("--scenario", choices=["conservative", "base", "aggressive"], default="base")
    parser.add_argument("--output-dir", default="output/multi-agent")
    args = parser.parse_args()
    message = " ".join(args.message) or f"Generate a quota report for {args.customer}"
    print(
        json.dumps(
            run_multi_agent_pipeline(
                message,
                customer_name=args.customer,
                data_source=args.data_source,
                scenario=args.scenario,
                output_dir=args.output_dir,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
