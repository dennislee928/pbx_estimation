# PBX Cloud RAG Engine

Cloud RAG endpoint for the PBX estimation frontend. It runs as a Cloudflare Worker and accepts the catalog payload already sent by the frontend:

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
  "solutions": [{ "name": "Grandstream UCM Series", "rank": 1, "reason": "..." }]
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

```bash
npm run deploy
```

After deploy, copy the Worker URL and set it as the repository secret:

```text
CLOUD_RAG_ENDPOINT=https://pbx-rag-engine.<your-account>.workers.dev/
```

The existing GitHub Actions workflow passes that secret into the frontend build as `NEXT_PUBLIC_CLOUD_RAG_ENDPOINT`.

## Configuration

- `USE_WORKERS_AI=true`: use Cloudflare Workers AI for the final recommendation paragraph.
- `USE_WORKERS_AI=false`: use only deterministic retrieval and extractive recommendation.
- `ALLOWED_ORIGINS=*`: CORS allowlist. Use a comma-separated list for production domains.

## Free-Tier Notes

Verified on June 4, 2026:

- Cloudflare Workers Free: 100,000 requests/day, 10 ms CPU time, 128 MB memory.
- Cloudflare Workers AI: included on Workers Free with 10,000 Neurons/day at no charge.
- Cloudflare Vectorize has a free tier, but this Worker does not require Vectorize because the frontend sends the current catalog payload directly.
