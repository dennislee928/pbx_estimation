# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# PBX Research MCP service
# A powerful research / crawl / validation / gathering / analysis / report
# microservice. Speaks MCP (stdio) and HTTP, and runs the repo's CI pipeline.
# Build from the repository root:
#   docker build -f services/research_mcp/Dockerfile -t pbx-research-mcp:local .
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PBX_WORKSPACE=/workspace \
    HOST=0.0.0.0 \
    PORT=8080 \
    RESEARCH_MCP_CONCURRENCY=8

# System libraries needed for lxml / trafilatura / charset detection, plus
# curl for the container healthcheck and git for any VCS-aware tooling.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev \
        libxslt1-dev \
        libz-dev \
        curl \
        ca-certificates \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies in two layers so source edits don't bust the dep cache.
# 1) Service runtime deps (HTTP, HTML/feeds parsing, analytics).
COPY services/research_mcp/requirements.txt /app/service-requirements.txt
# 2) Repo pipeline deps (pandas/scipy/lifelines/nbconvert for `generate`).
COPY requirements.txt /app/repo-requirements.txt

RUN python -m pip install --upgrade pip \
    && pip install -r /app/service-requirements.txt \
    && pip install -r /app/repo-requirements.txt

COPY services/research_mcp/server.py /app/server.py

# Non-root runtime. The mounted /workspace is read at runtime by the pipeline.
RUN useradd --create-home --uid 10001 research \
    && mkdir -p /workspace \
    && chown -R 10001:10001 /app /workspace
USER 10001

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/healthz" || exit 1

ENTRYPOINT ["python", "/app/server.py"]
CMD ["http"]
