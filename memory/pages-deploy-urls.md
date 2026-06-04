---
name: pages-deploy-urls
description: How the PBX Pages site is deployed, the two URLs, and the basePath/custom-domain trap
metadata:
  type: project
---

The frontend (`frontend/`, Next.js `output: export`) deploys to GitHub Pages via `.github/workflows/report.yml`. `next.config.mjs` bakes `basePath`/`assetPrefix` at build time from `NEXT_PUBLIC_SITE_BASE_PATH` (default `/pbx_estimation`).

Two possible URLs:
- Project URL: `https://dennislee928.github.io/pbx_estimation/zh/` — needs `basePath=/pbx_estimation`.
- Custom domain: `https://mtk-pbx-estimation.dennisleehappy.org/zh/` — needs `basePath=/` AND a `CNAME` file in the deployed artifact. Controlled by repo **variable** (not secret) `PAGES_CUSTOM_DOMAIN` (workflow reads `vars.PAGES_CUSTOM_DOMAIN`). When set, the build flips base path to `/` and writes `site/CNAME`.

Traps observed 2026-06-04:
- If `basePath` and serving URL mismatch, every `_next/static/...` asset 404s → CSS served as text/html (MIME refusal), JS blocked → React never hydrates → Sidebar (`onClick onSelect`) and the "Prioritize with Cloud RAG" button (`onClick askCloudRag`) are all dead. Interactivity == JS hydration.
- The custom domain is fronted by **Cloudflare** (`cf-cache-status: HIT`, `max-age=7200`); after a deploy the edge serves stale HTML for up to 2h. Purge Cloudflare (dashboard Purge Everything, or zone purge_cache API by host) or it looks unfixed. Cache-bust query (`?cb=...`) bypasses it to check origin.
- Reverting to an old commit (e.g. `7ebcc14a`, run #49) that lacks CNAME logic **unbinds the custom domain** (Pages `cname` → null, host shows "Site not found"); that version only works at the project URL.

The base-path-aware build that serves BOTH the custom-domain root and a `/pbx_estimation` fallback copy was at `340e523b` (saved in branch `origin/bak`).

RAG: tech-alternatives page POSTs `{scene, language, alternatives, solutions, ...}` to `NEXT_PUBLIC_CLOUD_RAG_ENDPOINT` = `https://pbxanalyze.pcleegood.workers.dev`. Worker verified live (zh + en return 200 with recommendations). See [[research-mcp-service]].
