import os

os.environ["PATH"] = r"C:\Program Files\Graphviz\bin;" + os.environ["PATH"]

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.aimachinelearning import BotServices, CognitiveServices
from diagrams.azure.analytics import DataLakeStoreGen1, SynapseAnalytics
from diagrams.azure.identity import ActiveDirectory
from diagrams.azure.web import AppServices
from diagrams.generic.storage import Storage

output_dir = os.path.join(
    os.environ["USERPROFILE"],
    "repos",
    "fabric-sales-agent-accelerator-scaffold",
    "docs",
    "diagrams",
)
output_file = os.path.join(output_dir, "architecture")

graph_attr = {"fontsize": "22", "bgcolor": "white", "pad": "1.0", "ranksep": "1.2", "nodesep": "0.8"}

with Diagram(
    "Fabric Sales Agent Accelerator",
    show=False,
    direction="LR",
    filename=output_file,
    outformat="png",
    graph_attr=graph_attr,
):
    with Cluster("User Interfaces"):
        m365 = CognitiveServices("M365\nCopilot")
        webapp = AppServices("Custom\nWeb App")
        ghcopilot = BotServices("GitHub Copilot\n(VS Code / CLI)")

    entra = ActiveDirectory("Microsoft\nEntra ID")

    with Cluster("Agent Orchestrator\n(Foundry / Copilot Studio /\nCopilot CLI Skills)"):
        agent = BotServices("Orchestrator")

    with Cluster("Sub-Agents"):
        fabric_agent = SynapseAnalytics("Fabric\nData Agent")
        researcher = CognitiveServices("Researcher\nAgent")
        sp_agent = Storage("SharePoint\nAgent")
        report_gen = AppServices("Report\nGenerator")

    onelake = DataLakeStoreGen1("OneLake\n(WWI Data)")

    m365 >> Edge(label="SSO") >> entra
    webapp >> Edge(label="SSO") >> entra
    ghcopilot >> Edge(label="SSO") >> entra
    entra >> Edge(label="Token") >> agent

    agent >> Edge(label="Query data", color="darkgreen") >> fabric_agent
    agent >> Edge(label="Research", color="darkorange") >> researcher
    agent >> Edge(label="Docs", color="blue") >> sp_agent
    agent >> Edge(label="Generate", color="purple") >> report_gen

    fabric_agent >> Edge(style="dashed") >> onelake

print("OK: architecture.png")
