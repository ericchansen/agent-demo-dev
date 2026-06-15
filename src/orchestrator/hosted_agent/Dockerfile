FROM python:3.11-slim

WORKDIR /app

COPY src/orchestrator/hosted_agent/requirements-hosted.txt .
RUN pip install --no-cache-dir -r requirements-hosted.txt

COPY src/ src/
COPY schemas/ schemas/
COPY fabric/ fabric/

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4).status==200 else 1)"]

CMD ["python", "-m", "src.orchestrator.hosted_agent.server"]
