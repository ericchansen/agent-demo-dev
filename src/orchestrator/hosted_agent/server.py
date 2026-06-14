"""Foundry invocation server for the Hosted Agent.

Receives HTTP requests from the Foundry managed runtime and dispatches
them to the agent pipeline. Uses the azure-ai-agentserver-invocations
package to handle the invocation protocol.

Reference: https://github.com/microsoft-foundry/foundry-samples
"""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

from src.orchestrator.hosted_agent import process_invocation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PORT = 8080


class InvocationHandler(BaseHTTPRequestHandler):
    """Handle Foundry agent invocation requests."""

    def do_POST(self) -> None:  # noqa: N802
        """Process incoming agent invocation."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            payload = json.loads(body)
            user_message = payload.get("input", payload.get("message", ""))
            result = process_invocation(user_message)

            response = json.dumps({"output": result})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response.encode())
        except Exception:
            logger.exception("Invocation failed")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Internal server error"}).encode())

    def do_GET(self) -> None:  # noqa: N802
        """Health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "healthy", "agent": "wwi-sales-hosted"}).encode())


def main() -> None:
    """Start the invocation server."""
    server = HTTPServer(("0.0.0.0", PORT), InvocationHandler)
    logger.info("Hosted Agent server starting on port %d", PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
