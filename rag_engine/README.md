---
title: PBX RAG Engine
emoji: PBX
colorFrom: teal
colorTo: blue
sdk: docker
app_port: 7860
---

# PBX Cloud RAG Engine

Cloud RAG endpoint for the PBX estimation frontend. It can run as either:

- A Cloudflare Worker that reads uploaded `reports/`, `data/processed/`, and `frontend/data/` assets from Cloudflare R2.
- A Hugging Face Docker Space that reads the same assets from `rag_engine/dist/hf_assets`.

It can also accept the catalog payload sent by the frontend:

```http
POST /
Content-Type: application/json
```

```json
{
  "scene": "hotel door relay low cost",
  "alternatives": [],
  "solutions": [],
  "crawler_seed_context": {}
}
```

Response:

```json
{
  "recommendation": "short cloud RAG recommendation",
  "alternatives": [{ "name": "Dry Contact / Relay Closure", "rank": 1, "reason": "..." }],
  "solutions": [{ "name": "Grandstream UCM Series", "rank": 1, "reason": "..." }],
  "documents": [{ "name": "reports/global_research_report_zh.md", "rank": 1, "excerpt": "..." }]
}
```

## Why Cloudflare Workers

I recommend Cloudflare Workers for this project because the official free plan currently includes 100,000 Worker requests per day, and Workers AI includes a daily free allocation. This service also has a deterministic no-paid-key fallback, so it remains usable when Workers AI is disabled or its free daily allocation is exhausted.

## Local Build

```bash
npm install
npm run build
npm test
```

## Deploy

### Cloudflare Worker

```bash
npm run deploy
```

Create the R2 bucket before deploying, or change `bucket_name` in `wrangler.toml`:

```bash
npx wrangler r2 bucket create auto-rag
```

After deploy, copy the Worker URL and set it as the repository secret:

```text
CLOUD_RAG_ENDPOINT=https://pbx-rag-engine.<your-account>.workers.dev/
```

The existing GitHub Actions workflow passes that secret into the frontend build as `NEXT_PUBLIC_CLOUD_RAG_ENDPOINT`.

### Hugging Face Docker Space

Hugging Face Spaces can host this self-developed RAG engine for free on CPU Basic. The Space must use Docker SDK and listen on `0.0.0.0:7860`; this directory includes the required `Dockerfile` and README metadata.

CI can upload this `rag_engine/` folder to a Space when these repository secrets are set:

- `HF_TOKEN`
- `HF_SPACE_ID`, for example `your-username/pbx-rag-engine`

The CI asset step generates `rag_engine/dist/hf_assets/`, so the Space can serve RAG from local files without Cloudflare R2.

Manual deploy:

```bash
hf repos create your-username/pbx-rag-engine --type space --space-sdk docker --exist-ok
hf upload your-username/pbx-rag-engine rag_engine --type space --commit-message "deploy rag engine"
```

Then set:

```text
CLOUD_RAG_ENDPOINT=https://your-username-pbx-rag-engine.hf.space/
```

## Configuration

- `USE_WORKERS_AI=true`: use Cloudflare Workers AI for the final recommendation paragraph.
- `USE_WORKERS_AI=false`: use only deterministic retrieval and extractive recommendation.
- `ALLOWED_ORIGINS=*`: CORS allowlist. Use a comma-separated list for production domains.
- `RAG_ASSET_PREFIX=latest`: R2 prefix for Cloudflare or local asset prefix for Hugging Face.
- `HF_RAG_ASSET_ROOT=/app/dist/hf_assets`: local asset root inside the Hugging Face Docker container.

## CI Asset Upload

The GitHub Actions workflow builds a manifest from:

- `reports/`
- `data/processed/`
- `frontend/data/`

Then it uploads those files to Cloudflare R2 when these repository secrets are present:

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_R2_BUCKET` (must match `auto-rag` unless `wrangler.toml` is changed)
- Optional S3 API upload secrets:
  - `CLOUDFLARE_R2_S3_ENDPOINT`, for example `https://8dfc8c4994bd0925c72ab9e2eff79b48.r2.cloudflarestorage.com/auto-rag`
  - `CLOUDFLARE_R2_S3_ACCESS_KEY_ID`
  - `CLOUDFLARE_R2_S3_SECRET_ACCESS_KEY`

The Worker reads:

- `latest/rag_engine/dist/rag_assets_manifest.json`
- `latest/frontend/data/awesome_list.json`
- `latest/frontend/data/solution_registry.json`
- `latest/frontend/data/crawler_seed_context.json`
- matching report/data text assets for document evidence.

## NotebookLM

Google NotebookLM does not provide an official public upload API. CI therefore creates a NotebookLM-ready manual source bundle at:

```text
rag_engine/dist/notebooklm_sources/
```

The bundle is capped at 50 sources and prioritizes generated reports and processed data. It is included in the workflow artifact.

If you run an unofficial bridge such as `notebooklm-rest-api` or `notebooklm-py`, set:

- `NOTEBOOKLM_UPLOAD_URL`
- `NOTEBOOKLM_API_TOKEN` if your bridge requires it

The workflow will then post the selected source files to that endpoint. This is intentionally opt-in because unofficial NotebookLM automation depends on browser/session internals and can break when Google changes the web app.

## Free-Tier Notes

Verified on June 4, 2026:

- Cloudflare Workers Free: 100,000 requests/day, 10 ms CPU time, 128 MB memory.
- Cloudflare Workers AI: included on Workers Free with 10,000 Neurons/day at no charge.
- Cloudflare R2 has a free tier suitable for staging this repository's generated report/data assets.
- Cloudflare Vectorize has a free tier, but this Worker does not require Vectorize because the catalog and document assets are retrieved from R2.
