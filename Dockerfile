# ---- Build stage ----
FROM python:3.12-slim AS builder

WORKDIR /build
COPY . .

RUN pip install --no-cache-dir build && \
    python -m build --wheel

# ---- Runtime stage ----
FROM python:3.12-slim

WORKDIR /app

# Install runtime deps + cogni-agent
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && \
    rm /tmp/*.whl

# Create a non-root user
RUN useradd --create-home --shell /bin/bash cogni
USER cogni

# Entrypoint: run a Python REPL with cogni_agent pre-imported
ENTRYPOINT ["python3", "-c", "from cogni_agent import AgentRuntime, AgentBuilder; from cogni_agent.tools import *; print('CogniAgent loaded. Use agent = await AgentRuntime.create(name=...)')"]

CMD ["python3"]