#!/usr/bin/env python3
"""Golden-QA evaluation harness for the Fabric Data Agent.

Reads question/expected-answer pairs from golden-qa.json, sends each question
to the Data Agent (or a mock), scores the responses, and prints a summary.

Usage:
    python tests/eval/run_eval.py                     # live Data Agent
    python tests/eval/run_eval.py --mock               # mock mode (canned answers)
    python tests/eval/run_eval.py --pass-rate 90       # require 90% to pass
    python tests/eval/run_eval.py --category top-n     # run only top-n questions
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

GOLDEN_QA_PATH = Path(__file__).parent / "golden-qa.json"

# ── Mock answers ────────────────────────────────────────────────────────────
# Keyword-triggered canned responses used when --mock is set.  Each mock
# tries to include enough keywords to pass the expected_contains checks.

_MOCK_ANSWERS: dict[str, str] = {
    "top 5 customers": (
        "The top 5 customers by revenue are: 1. Tailspin Toys (Head Office) — $1.2M, "
        "2. Wingtip Toys (Head Office) — $980K, 3. Contoso Ltd — $870K, "
        "4. Fabrikam Inc — $750K, 5. Northwind Traders — $620K."
    ),
    "best-selling stock item": (
        "The best-selling stock items by quantity are: "
        "1. USB food flash drive - pizza slice, "
        "2. USB food flash drive - hamburger, "
        "3. Novelty chilli chocolate. "
        "The stock item category leader is USB novelties."
    ),
    "top 3 best-selling": (
        "The top 3 best-selling stock items by quantity: "
        "1. USB food flash drive - pizza slice (42K units), "
        "2. USB food flash drive - hamburger (38K units), "
        "3. Novelty chilli chocolate (31K units)."
    ),
    "cities generated the most": ("Top cities by sales: New York, Los Angeles, Chicago, Houston, Phoenix."),
    "top 3 salespersons": (
        "The top 3 salespersons by total sales are: Salesperson #1 Amy, Salesperson #2 Archer, Salesperson #3 Hudson."
    ),
    "top 10 customers in the midwest": (
        "Top Midwest customers: Tailspin Toys, Wingtip Toys, Contoso Ltd, Fabrikam Inc, Northwind Traders (and 5 more)."
    ),
    "total sales revenue in 2016": "Total sales revenue in 2016 was $14.3M.",
    "total orders were placed in 2015": "There were 31,247 orders placed in 2015.",
    "average order value": "The average order value across all sales is $247.50.",
    "total quantity of items sold in 2016": ("Total quantity of items sold in 2016 was 1,045,832 units."),
    "distinct customers made purchases in 2016": ("402 distinct customers made purchases in 2016."),
    "total tax collected": "The total tax collected across all sales is $2.1M.",
    "tailspin toys (head office)": ("Tailspin Toys (Head Office) has 4,321 transactions totalling $1.2M."),
    "sales in new york": "Sales in New York totalled $890K across 2,100 orders.",
    "profit margin was negative": ("There are 47 transactions where the profit margin was negative."),
    "sales of usb novelty": "USB novelty items generated $320K in revenue across 8,400 units.",
    "wingtip toys in 2016": ("Wingtip Toys total sales in 2016: $540K across 1,200 orders."),
    "quantity exceeded 500": ("There are 12 orders where quantity exceeded 500 units in a single order."),
    "month over month in 2016": (
        "Monthly sales in 2016: January $1.1M, February $1.0M, March $1.2M, "
        "April $1.15M, May $1.3M, June $1.1M, July $1.2M, August $1.25M, "
        "September $1.1M, October $1.3M, November $1.35M, December $1.4M."
    ),
    "quarterly sales trend for 2015": ("2015 quarterly sales: Q1 $3.2M, Q2 $3.5M, Q3 $3.4M, Q4 $3.8M."),
    "compare sales revenue between 2015 and 2016": (
        "2015 total: $13.9M, 2016 total: $14.3M — a 2.9% year-over-year increase."
    ),
    "tailspin toys purchasing volume": ("Tailspin Toys purchasing volume increased 15% from 2015 to 2016."),
    "year-over-year growth": ("Year-over-year revenue growth rate is 2.9% (2015 to 2016)."),
    "growth rate": ("The year-over-year growth rate in total revenue is approximately 2.9%."),
    "total revenue from tailspin toys": ("Total revenue from Tailspin Toys across all locations: $2.4M."),
    "buying group": ("There are 2 buying groups in the customer dimension: Tailspin Toys and Wingtip Toys."),
    "how many buying": ("There are 2 buying group entries in the customer dimension: Tailspin Toys and Wingtip Toys."),
    "usb food flash drive - pizza slice": (
        "The stock item 'USB food flash drive - pizza slice' belongs to the USB Novelties category."
    ),
    "salesperson for contoso": ("The primary salesperson assigned to Contoso Ltd is Archer Lamble."),
    "best-selling stock items by total revenue": (
        "Best-selling stock items by revenue: 1. DBA joke mug, 2. USB food flash drive, 3. Novelty chilli chocolate."
    ),
    "highest total sales in 2016": ("The salesperson with the highest total sales in 2016 was Amy Trefl."),
    "revenue breakdown by product category": (
        "Revenue by category: Novelty goods $5.2M, USB novelties $3.8M, Clothing $2.9M, Packaging materials $2.4M."
    ),
    "southeast sales territory": ("Total sales for the Southeast territory: $2.1M across 5,400 orders."),
}


def _mock_answer(question: str) -> str:
    """Return a canned answer matching the question by keyword overlap."""
    q_lower = question.lower()
    best_key = ""
    best_overlap = 0
    for key in _MOCK_ANSWERS:
        overlap = sum(1 for word in key.split() if word in q_lower)
        if overlap > best_overlap:
            best_overlap = overlap
            best_key = key
    if best_key:
        return _MOCK_ANSWERS[best_key]
    return f"I found results related to your question about Wide World Importers: {question}"


# ── Data Agent client ───────────────────────────────────────────────────────


def _live_answer(question: str) -> str:
    """Send a question to the Fabric Data Agent and return its answer."""
    try:
        from fabric_data_agent_client import FabricDataAgentClient  # type: ignore[import-untyped]

        client = FabricDataAgentClient()
        response = client.query(question)
        return response.get("answer", response.get("text", str(response)))
    except ImportError:
        raise RuntimeError(
            "fabric_data_agent_client is not installed. "
            "Use --mock for testing without a live Data Agent, or install the SDK."
        ) from None


# ── Scoring ─────────────────────────────────────────────────────────────────


@dataclass
class EvalResult:
    question: str
    category: str
    answer: str
    passed: bool
    missing: list[str] = field(default_factory=list)
    unexpected: list[str] = field(default_factory=list)


def score_answer(qa: dict, answer: str) -> EvalResult:
    """Score a single answer against expected_contains / expected_not_contains."""
    answer_lower = answer.lower()
    missing = [term for term in qa.get("expected_contains", []) if term.lower() not in answer_lower]
    unexpected = [term for term in qa.get("expected_not_contains", []) if term.lower() in answer_lower]
    passed = len(missing) == 0 and len(unexpected) == 0
    return EvalResult(
        question=qa["question"],
        category=qa.get("category", "unknown"),
        answer=answer,
        passed=passed,
        missing=missing,
        unexpected=unexpected,
    )


# ── Main ────────────────────────────────────────────────────────────────────


def load_golden_qa(path: Path, category: str | None = None) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        qa_list: list[dict] = json.load(f)
    if category:
        qa_list = [q for q in qa_list if q.get("category") == category]
    return qa_list


def run_eval(
    qa_list: list[dict],
    *,
    mock: bool = False,
    verbose: bool = False,
) -> list[EvalResult]:
    ask = _mock_answer if mock else _live_answer
    results: list[EvalResult] = []

    for i, qa in enumerate(qa_list, 1):
        question = qa["question"]
        label = question[:72] + "…" if len(question) > 72 else question
        print(f"  [{i:>2}/{len(qa_list)}] {label}", end="", flush=True)

        t0 = time.monotonic()
        answer = ask(question)
        elapsed = time.monotonic() - t0

        result = score_answer(qa, answer)
        results.append(result)

        status = "✓" if result.passed else "✗"
        print(f"  {status} ({elapsed:.1f}s)")

        if verbose and not result.passed:
            if result.missing:
                print(f"         missing: {result.missing}")
            if result.unexpected:
                print(f"         unexpected: {result.unexpected}")

    return results


def print_summary(results: list[EvalResult], min_pass_rate: float) -> bool:
    """Print evaluation summary. Returns True if pass rate meets threshold."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    pass_rate = (passed / total * 100) if total else 0

    # Category breakdown
    categories: dict[str, list[EvalResult]] = {}
    for r in results:
        categories.setdefault(r.category, []).append(r)

    print(f"\n{'═' * 55}")
    print("  Evaluation Summary")
    print(f"{'═' * 55}")
    print(f"  Total:     {total}")
    print(f"  Passed:    {passed}")
    print(f"  Failed:    {failed}")
    print(f"  Pass rate: {pass_rate:.1f}% (threshold: {min_pass_rate:.0f}%)")
    print(f"{'─' * 55}")

    print("  By category:")
    for cat, cat_results in sorted(categories.items()):
        cat_pass = sum(1 for r in cat_results if r.passed)
        cat_total = len(cat_results)
        pct = cat_pass / cat_total * 100 if cat_total else 0
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"    {cat:<14s} {bar} {cat_pass}/{cat_total} ({pct:.0f}%)")

    if failed:
        print(f"\n{'─' * 55}")
        print("  Failures:")
        for r in results:
            if not r.passed:
                print(f"    ✗ [{r.category}] {r.question}")
                if r.missing:
                    print(f"      missing: {r.missing}")
                if r.unexpected:
                    print(f"      unexpected: {r.unexpected}")

    print(f"{'═' * 55}")
    meets = pass_rate >= min_pass_rate
    verdict = "PASS ✓" if meets else "FAIL ✗"
    print(f"  Result: {verdict}")
    print(f"{'═' * 55}\n")
    return meets


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run golden-QA evaluation against the Fabric Data Agent")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use canned mock answers instead of a live Data Agent",
    )
    parser.add_argument(
        "--qa-file",
        type=Path,
        default=GOLDEN_QA_PATH,
        help=f"Path to golden-qa.json (default: {GOLDEN_QA_PATH})",
    )
    parser.add_argument(
        "--pass-rate",
        type=float,
        default=80.0,
        help="Minimum pass rate percentage to exit 0 (default: 80)",
    )
    parser.add_argument(
        "--category",
        choices=["top-n", "aggregation", "filter", "trend", "lookup"],
        default=None,
        help="Run only questions in this category",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show failure details inline during evaluation",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.qa_file.exists():
        print(f"Error: golden-qa file not found: {args.qa_file}", file=sys.stderr)
        return 1

    qa_list = load_golden_qa(args.qa_file, category=args.category)
    if not qa_list:
        print("No questions to evaluate.", file=sys.stderr)
        return 1

    mode = "mock" if args.mock else "live"
    cat_label = f" [{args.category}]" if args.category else ""
    print(f"\n{'═' * 55}")
    print(f"  Fabric Data Agent — Golden QA Eval ({mode}){cat_label}")
    print(f"  {len(qa_list)} questions")
    print(f"{'═' * 55}\n")

    results = run_eval(qa_list, mock=args.mock, verbose=args.verbose)
    meets_threshold = print_summary(results, args.pass_rate)

    return 0 if meets_threshold else 1


if __name__ == "__main__":
    sys.exit(main())
