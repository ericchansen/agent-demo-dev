FROM python:3.11-slim

WORKDIR /app

COPY src/orchestrator/hosted_agent/requirements-hosted.txt .
RUN pip install --no-cache-dir -r requirements-hosted.txt

COPY src/ src/
COPY schemas/ schemas/
COPY fabric/ fabric/

EXPOSE 8080

CMD ["python", "-m", "src.orchestrator.hosted_agent.server"]
