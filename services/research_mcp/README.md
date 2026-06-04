# PBX Research MCP Service

Dockerized research/crawler/validation service for this repository.

It has two entry points:

- CI runner commands for deterministic report generation.
- A lightweight MCP-compatible stdio server exposing tools for agents.

The service intentionally reuses the repository's existing Python modules and scripts instead of creating a second crawler implementation.

## Build

From the repository root:

```bash
docker build -f services/research_mcp/Dockerfile -t pbx-research-mcp:local .
```

## Choreo Deployment

Use port `8080`.

The repository root contains `.choreo/component.yaml` for Choreo Dockerfile builds. The Docker image starts the HTTP service by default with:

```bash
python /app/server.py http
```

Available HTTP endpoints:

- `GET /healthz`
- `GET /validate`
- `GET /analyze?scene=hotel%20door%20relay&top_k=5`
- `POST /analyze`
- `POST /generate`

## CI/CLI Usage

Generate crawler seed context, shared research outputs, reports, and validation summary:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  -e PBX_WORKSPACE=/workspace \
  pbx-research-mcp:local generate
```

Validate generated assets:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  -e PBX_WORKSPACE=/workspace \
  pbx-research-mcp:local validate
```

Analyze a scene against the generated catalog:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  -e PBX_WORKSPACE=/workspace \
  pbx-research-mcp:local analyze "hotel door relay non RF"
```

## MCP Usage

Run the stdio MCP server:

```bash
docker run --rm -i \
  -v "$PWD:/workspace" \
  -e PBX_WORKSPACE=/workspace \
  pbx-research-mcp:local mcp
```

Supported MCP tools:

- `generate_research_outputs`
- `validate_research_outputs`
- `analyze_scene`

The implementation speaks JSON-RPC over stdin/stdout and supports `initialize`, `tools/list`, and `tools/call`.

## CI Integration

`.github/workflows/report.yml` builds this image and uses it for:

- initial crawler seed/shared research output generation
- post-notebook research output refresh and validation

The workflow still uses the normal Python environment for notebooks and nbconvert.
