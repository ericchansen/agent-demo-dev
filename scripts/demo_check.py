#!/usr/bin/env python3
"""Run local demo-readiness checks for the Fabric Sales Agent Accelerator."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EXPECTED_MCP_SERVERS = {
    "fabric-core",
    "wwi-sales-data",
    "market-data",
    "researcher-agent",
    "sharepoint-agent",
    "report-generator",
    "quota-estimator",
}
EXPECTED_FOUNDRY_HANDLERS = {
    "databricks_query",
    "forecast_quota",
    "generate_quota_estimation_report",
    "generate_report",
    "web_research",
    "compute_quota_attainment",
    "get_account_activity",
}
EXPECTED_HOSTED_TOOLS = EXPECTED_FOUNDRY_HANDLERS | {"fabric_query"}
DEFAULT_RESOURCE_GROUP = "rg-fabric-agent-dev"
DEFAULT_COG_SERVICES_NAME = "fabricagentaidev2026"


def _resource_group() -> str:
    return os.environ.get("AZURE_RESOURCE_GROUP", DEFAULT_RESOURCE_GROUP)


def _cog_services_resource_id() -> str:
    """Resolve the Foundry AI Services account resource ID from env."""
    explicit = os.environ.get("FSA_COG_SERVICES_RESOURCE_ID", "").strip()
    if explicit:
        return explicit
    subscription = os.environ.get("AZURE_SUBSCRIPTION_ID", "").strip()
    if not subscription:
        raise RuntimeError(
            "Set FSA_COG_SERVICES_RESOURCE_ID, or AZURE_SUBSCRIPTION_ID (with optional "
            "AZURE_RESOURCE_GROUP / FSA_COG_SERVICES_NAME), before running the --azure check."
        )
    cog_name = os.environ.get("FSA_COG_SERVICES_NAME", DEFAULT_COG_SERVICES_NAME)
    return (
        f"/subscriptions/{subscription}/resourceGroups/{_resource_group()}/"
        f"providers/Microsoft.CognitiveServices/accounts/{cog_name}"
    )


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class BackendReadiness:
    name: str
    ready: bool
    auth: str
    hint: str


def _env_set(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def live_backend_readiness() -> list[BackendReadiness]:
    """Report which live backends are configured and what is missing to prove each.

    Purely informational: a backend being unconfigured is expected for offline runs and
    never fails the readiness gate. The matrix tells a facilitator exactly which secrets
    to add to flip a backend from skipped to live-proven.
    """
    from src.orchestrator.fabric_mcp_client import fabric_spn_status

    rows: list[BackendReadiness] = []

    # Foundry — account-based project registration.
    foundry_required = [
        "AZURE_CLIENT_ID",
        "AZURE_TENANT_ID",
        "AZURE_SUBSCRIPTION_ID",
        "FOUNDRY_PROJECT_ENDPOINT",
        "MODEL_DEPLOYMENT_NAME",
    ]
    foundry_missing = [name for name in foundry_required if not _env_set(name)]
    rows.append(
        BackendReadiness(
            name="Foundry",
            ready=not foundry_missing,
            auth="OIDC / DefaultAzureCredential",
            hint="ready" if not foundry_missing else "set " + ", ".join(foundry_missing),
        )
    )

    # Fabric — endpoint config plus an auth mode (SPN triple or DefaultAzureCredential).
    fabric_endpoint_ok = _env_set("FABRIC_MCP_URL") or (
        _env_set("FABRIC_WORKSPACE_ID") and _env_set("FABRIC_DATA_AGENT_ID")
    )
    fabric_mode, fabric_spn_missing = fabric_spn_status()
    fabric_auth = {
        "service-principal": "service-principal (ClientSecretCredential)",
        "default": "DefaultAzureCredential",
        "partial": "partial service-principal",
    }[fabric_mode]
    fabric_hints: list[str] = []
    if not fabric_endpoint_ok:
        fabric_hints.append("set FABRIC_MCP_URL or FABRIC_WORKSPACE_ID + FABRIC_DATA_AGENT_ID")
    if fabric_mode == "partial":
        fabric_hints.append("complete Fabric SPN: also set " + " + ".join(fabric_spn_missing))
    rows.append(
        BackendReadiness(
            name="Fabric",
            ready=fabric_endpoint_ok and fabric_mode != "partial",
            auth=fabric_auth,
            hint="ready" if not fabric_hints else "; ".join(fabric_hints),
        )
    )

    # Databricks Genie — managed MCP or SDK-direct transport, with a token or OAuth M2M.
    dbx_auth_ok = _env_set("DATABRICKS_TOKEN") or (
        _env_set("DATABRICKS_CLIENT_ID") and _env_set("DATABRICKS_CLIENT_SECRET")
    )
    dbx_managed = _env_set("DATABRICKS_GENIE_MCP_URL")
    dbx_direct = (_env_set("DATABRICKS_HOST") or _env_set("DATABRICKS_WORKSPACE_URL")) and _env_set(
        "DATABRICKS_GENIE_SPACE_ID"
    )
    dbx_hints = []
    if not (dbx_managed or dbx_direct):
        dbx_hints.append("set DATABRICKS_GENIE_MCP_URL (managed MCP) or DATABRICKS_HOST + DATABRICKS_GENIE_SPACE_ID")
    if not dbx_auth_ok:
        dbx_hints.append("set DATABRICKS_TOKEN or DATABRICKS_CLIENT_ID + DATABRICKS_CLIENT_SECRET")
    rows.append(
        BackendReadiness(
            name="Databricks",
            ready=(dbx_managed or dbx_direct) and dbx_auth_ok,
            auth="OAuth M2M"
            if (_env_set("DATABRICKS_CLIENT_ID") and not _env_set("DATABRICKS_TOKEN"))
            else "token/PAT",
            hint="ready" if not dbx_hints else "; ".join(dbx_hints),
        )
    )
    return rows


def print_backend_readiness(rows: list[BackendReadiness]) -> None:
    print("\nLive backend readiness")
    print("----------------------")
    for row in rows:
        status = "READY" if row.ready else "SKIP "
        print(f"[{status}] {row.name:<11s} auth={row.auth} :: {row.hint}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run demo-readiness checks.")
    parser.add_argument("--azure", action="store_true", help="Check live dev Azure public network access.")
    parser.add_argument("--docker", action="store_true", help="Build and smoke-test the hosted-agent Docker image.")
    args = parser.parse_args()

    checks: list[tuple[str, Callable[[], str]]] = [
        ("MCP config", check_mcp_configs),
        ("Foundry tools", check_foundry_tools),
        ("Quota artifacts", check_quota_artifacts),
        ("Hosted runtime", check_hosted_runtime),
    ]
    if args.azure:
        checks.append(("Azure PNA", check_azure_public_network_access))
    if args.docker:
        checks.append(("Docker hosted smoke", check_docker_smoke))

    results: list[CheckResult] = []
    for name, check in checks:
        try:
            detail = check()
        except Exception as exc:  # pragma: no cover - exercised by operator failures
            results.append(CheckResult(name=name, passed=False, detail=str(exc)))
        else:
            results.append(CheckResult(name=name, passed=True, detail=detail))

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")

    print_backend_readiness(live_backend_readiness())

    return 0 if all(result.passed for result in results) else 1


def check_mcp_configs() -> str:
    paths = [
        ROOT / ".github" / "mcp.json",
        ROOT / ".vscode" / "mcp.json",
        ROOT / "src" / "cli" / "mcp-config.json",
    ]
    server_sets: dict[str, set[str]] = {}
    for path in paths:
        payload = _load_json_without_duplicate_keys(path)
        servers = payload.get("mcpServers")
        if not isinstance(servers, dict):
            raise ValueError(f"{path} is missing top-level mcpServers.")

        names = set(servers)
        missing = EXPECTED_MCP_SERVERS - names
        extra = names - EXPECTED_MCP_SERVERS
        if missing or extra:
            raise ValueError(f"{path} server mismatch. missing={sorted(missing)} extra={sorted(extra)}")

        for server_name, server in servers.items():
            if not isinstance(server, dict):
                raise ValueError(f"{path}:{server_name} must be an object.")
            if not isinstance(server.get("description"), str) or len(str(server["description"])) < 10:
                raise ValueError(f"{path}:{server_name} is missing a useful description.")
            server_type = server.get("type")
            if server_type == "http" and not isinstance(server.get("url"), str):
                raise ValueError(f"{path}:{server_name} HTTP server is missing url.")
            if server_type == "stdio" and not isinstance(server.get("command"), str):
                raise ValueError(f"{path}:{server_name} stdio server is missing command.")
            if server_type not in {"http", "stdio"}:
                raise ValueError(f"{path}:{server_name} has unsupported type {server_type!r}.")

        server_sets[str(path.relative_to(ROOT))] = names

    if len({tuple(sorted(names)) for names in server_sets.values()}) != 1:
        raise ValueError(f"MCP server sets differ: {server_sets}")
    return f"{len(paths)} registries include {len(EXPECTED_MCP_SERVERS)} servers"


def check_foundry_tools() -> str:
    from src.orchestrator.config import OrchestratorConfig
    from src.orchestrator.foundry_agent import _build_tools

    config = OrchestratorConfig(
        foundry_project_endpoint="https://example.ai.azure.com/",
        model_deployment_name="gpt-4o",
        fabric_iq_connection_id="/subscriptions/example/connections/wwi",
        market_data_connection_id="/subscriptions/example/connections/market",
        workiq_connection_id=None,
    )
    tools, handlers = _build_tools(config)
    tool_names = {str(getattr(tool, "name")) for tool in tools if getattr(tool, "name", None)}
    missing_handlers = EXPECTED_FOUNDRY_HANDLERS - set(handlers)
    if missing_handlers:
        raise ValueError(f"Missing Foundry handlers: {sorted(missing_handlers)}")
    missing_tools = EXPECTED_FOUNDRY_HANDLERS - tool_names
    if missing_tools:
        raise ValueError(f"Missing Foundry tool registrations: {sorted(missing_tools)}")
    if "real_world_market_data" not in tool_names:
        raise ValueError("Market-data FabricIQPreviewTool is not registered.")
    return f"{len(tool_names)} tools registered, {len(handlers)} local handlers"


def check_quota_artifacts() -> str:
    from src.agents.quota_estimator.pipeline import (
        demo_research_data,
        demo_sales_rows,
        demo_workiq_activity,
        generate_quota_estimation_report,
    )

    with tempfile.TemporaryDirectory() as tmp:
        result = generate_quota_estimation_report(
            customer_name="Tailspin Toys",
            sales_rows=demo_sales_rows(),
            research_data=demo_research_data("Tailspin Toys"),
            workiq_activity=demo_workiq_activity("Tailspin Toys"),
            output_dir=tmp,
            formats=["xlsx", "html", "pdf"],
        )
        artifacts = result.get("artifacts")
        if not isinstance(artifacts, dict):
            raise ValueError("Quota result did not include artifacts.")
        missing = {"xlsx", "html", "pdf"} - set(artifacts)
        if missing:
            raise ValueError(f"Quota artifacts missing formats: {sorted(missing)}")
        for fmt, path in artifacts.items():
            artifact_path = Path(str(path))
            if not artifact_path.exists() or artifact_path.stat().st_size <= 0:
                raise ValueError(f"{fmt} artifact is missing or empty: {artifact_path}")
    return "XLSX, HTML, and PDF artifacts generated"


def check_hosted_runtime() -> str:
    from src.orchestrator import hosted_agent

    tool_names = {tool["function"]["name"] for tool in hosted_agent.TOOLS}
    missing = EXPECTED_HOSTED_TOOLS - tool_names
    if missing:
        raise ValueError(f"Hosted tools missing: {sorted(missing)}")

    with tempfile.TemporaryDirectory() as tmp:
        previous = os.environ.get("HOSTED_AGENT_OUTPUT_DIR")
        os.environ["HOSTED_AGENT_OUTPUT_DIR"] = tmp
        try:
            response = hosted_agent.process_invocation("Generate a quota report for Tailspin Toys")
        finally:
            if previous is None:
                os.environ.pop("HOSTED_AGENT_OUTPUT_DIR", None)
            else:
                os.environ["HOSTED_AGENT_OUTPUT_DIR"] = previous
        if "Generated a quota estimation report" not in response:
            raise ValueError(f"Unexpected hosted response: {response[:200]}")
        expected = {
            "tailspin_toys_base_quota_estimate.xlsx",
            "tailspin_toys_base_quota_estimate.html",
            "tailspin_toys_base_quota_estimate.pdf",
        }
        produced = {path.name for path in Path(tmp).iterdir()}
        missing_artifacts = expected - produced
        if missing_artifacts:
            raise ValueError(f"Hosted runtime missing artifacts: {sorted(missing_artifacts)}")
    return f"{len(tool_names)} hosted tools wired"


def check_azure_public_network_access() -> str:
    if _az_command() is None:
        raise RuntimeError("Azure CLI is not available on PATH.")

    resource_group = _resource_group()

    # Check the AI Services (Foundry) account
    cog_pna = _az_json(
        [
            "resource",
            "show",
            "--ids",
            _cog_services_resource_id(),
            "--api-version",
            "2024-10-01",
            "--query",
            "properties.publicNetworkAccess",
        ]
    )
    if cog_pna != "Enabled":
        raise ValueError(f"AI Services account publicNetworkAccess is {cog_pna!r}, expected 'Enabled'.")

    cognitive_ids = _az_json(
        [
            "resource",
            "list",
            "-g",
            resource_group,
            "--resource-type",
            "Microsoft.CognitiveServices/accounts",
            "--query",
            "[].id",
        ]
    )
    cognitive = [
        _az_json(
            [
                "resource",
                "show",
                "--ids",
                resource_id,
                "--api-version",
                "2024-10-01",
                "--query",
                "{name:name,pna:properties.publicNetworkAccess,defaultAction:properties.networkAcls.defaultAction}",
            ]
        )
        for resource_id in cognitive_ids
    ]
    storage = _az_json(
        [
            "storage",
            "account",
            "list",
            "-g",
            resource_group,
            "--query",
            "[].{name:name,pna:publicNetworkAccess,defaultAction:networkRuleSet.defaultAction}",
        ]
    )
    for resource in [*cognitive, *storage]:
        if resource.get("pna") != "Enabled":
            raise ValueError(f"{resource.get('name')} publicNetworkAccess is {resource.get('pna')!r}.")
        if resource.get("defaultAction") not in (None, "Allow"):
            raise ValueError(f"{resource.get('name')} defaultAction is {resource.get('defaultAction')!r}.")
    return f"{len(cognitive)} cognitive and {len(storage)} storage resources are reachable"


def check_docker_smoke() -> str:
    if shutil.which("docker") is None:
        raise RuntimeError("Docker is not available on PATH.")
    image = "agent-demo-hosted:demo-check"
    _run(["docker", "build", "-f", "src/orchestrator/hosted_agent/Dockerfile", "-t", image, "."], timeout=300)
    output = _run(
        [
            "docker",
            "run",
            "--rm",
            image,
            "python",
            "-c",
            "import src.orchestrator.hosted_agent as h; print(h.process_invocation('status')[:120])",
        ],
        timeout=120,
    )
    if "Hosted WWI sales agent is ready" not in output:
        raise ValueError(f"Unexpected Docker smoke output: {output[:200]}")
    return f"{image} built and imported"


def _load_json_without_duplicate_keys(path: Path) -> dict[str, Any]:
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: set[str] = set()
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in seen:
                raise ValueError(f"{path} contains duplicate key {key!r}.")
            seen.add(key)
            result[key] = value
        return result

    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle, object_pairs_hook=hook)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _az_json(args: list[str]) -> Any:
    az_command = _az_command()
    if az_command is None:
        raise RuntimeError("Azure CLI is not available on PATH.")
    text = _run([az_command, *args, "-o", "json"], timeout=120)
    return json.loads(text)


def _az_command() -> str | None:
    return shutil.which("az") or shutil.which("az.cmd")


def _run(command: list[str], *, timeout: int) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{' '.join(command)} failed with exit code {result.returncode}: {(result.stderr or result.stdout).strip()}"
        )
    return result.stdout.strip()


if __name__ == "__main__":
    sys.exit(main())
