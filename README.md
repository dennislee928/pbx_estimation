# PBX Market Estimation & VoIP Trend Forecasting

[Report Generation](https://github.com/dennis-lee/pbx_estimation/actions/workflows/report.yml)

---

**English** | [中文](#chinese)

---

<a id="english"></a>

## Overview

Quantitative forecasting of PBX market decline and VoIP adoption across 12+ countries using time-series analysis and survival models.

### The Problem

Traditional PBX (Private Branch Exchange) systems are being rapidly replaced by VoIP/Cloud-based solutions. This project applies data science to answer two core questions:

1. **Trend by Country** — When will the traditional PBX market die in each country? (Logistic Growth / S-Curve)
2. **Product Success Rate** — What is the survival probability of a new PBX gateway product launched in a shrinking market? (Cox Proportional Hazards Model)

### Mathematical Framework

#### 1. S-Curve (Logistic Growth Model) — Trend Prediction

$$P(t) = \frac{K}{1 + e^{-r(t - t_0)}}$$

| Parameter | Meaning |
|-----------|---------|
| $P(t)$ | Market penetration at time $t$ |
| $K$ | Carrying capacity (maximum market size) |
| $r$ | Growth/decay rate |
| $t_0$ | Inflection point (fastest change) |

Implemented via `scipy.optimize.curve_fit` per country. Outputs: saturation/death year for each market.

#### 2. Cox Proportional Hazards Model — Product Survival

$$h(t|X) = h_0(t) \exp(\sum_{i=1}^n \beta_i X_i)$$

| Parameter | Meaning |
|-----------|---------|
| $h(t\|X)$ | Hazard (failure risk) at time $t$ given covariates $X$ |
| $h_0(t)$ | Baseline hazard |
| $X_i$ | Covariates (PSTN phase-out policy, broadband penetration, etc.) |
| $\beta_i$ | Weight of each covariate |

Implemented via `lifelines.CoxPHFitter`. Outputs: survival curves and hazard ratios per country.

### Countries Covered

| Region | Countries |
|--------|-----------|
| **Asia-Pacific** | Taiwan, Japan, South Korea, China, India |
| **Europe** | UK, Germany, France, Sweden, Italy |
| **Americas** | US, Canada, Brazil |

### Data Sources

| Source | Data | Method |
|--------|------|--------|
| **World Bank API** | Fixed telephone subscriptions, broadband penetration | `wbgapi` |
| **ITU ICT Indicators** | IP communication share, infrastructure scores | ITU DataHub API (`api.datahub.itu.int`) |
| **BEREC** (European Regulators) | Copper switch-off dates per country | PDF scraping (Table 3) |
| **UK House of Commons Library** | UK PSTN switch-off timeline | PDF/HTML scrape (`CBP-9471`) |
| **CEPT** | European IP migration status | ECC Report 265 PDF scrape |
| **NCC (Taiwan)** | Local telecom statistics | NCC API + MODA open data (`data.gov.tw`) |

### Project Structure

```
pbx_estimation/
├── data/
│   ├── raw/          # API downloads cache
│   └── processed/    # Cleaned panel data
├── notebooks/
│   ├── 01_fetch_data.ipynb           # Data collection
│   ├── 01b_fetch_supplementary_sources.ipynb  # ITU / UK / CEPT / NCC crawlers
│   ├── 02_eda_visualization.ipynb    # Exploratory analysis
│   ├── 03_logistic_growth.ipynb      # S-Curve fitting
│   └── 04_survival_analysis.ipynb    # CoxPH model
├── src/
│   ├── data/fetcher.py
│   ├── data/supplementary_fetcher.py
│   ├── data/preprocessor.py
│   ├── models/logistic_growth.py
│   └── models/survival.py
├── tests/
├── .github/workflows/report.yml      # Auto-generate reports
├── config.yaml
├── requirements.txt
└── pyproject.toml
```

### Getting Started

```bash
# Clone & install
git clone https://github.com/dennis-lee/pbx_estimation.git
cd pbx_estimation
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run notebooks
jupyter notebook notebooks/
```

### Report Generation via GitHub Actions

Reports are automatically generated and published via a scheduled GitHub Actions workflow:

- **Schedule**: Runs every hour at minute 0 UTC
- **Trigger**: Also supports manual dispatch via GitHub UI
- **Steps**:
  1. Fetch latest data from World Bank / ITU / BEREC APIs
  2. Execute all Jupyter notebooks in order
  3. Render notebooks to HTML and PDF
  4. Archive reports as build artifacts (downloadable from Actions tab)
  5. Optionally deploy to GitHub Pages for a live dashboard

> 💡 **Manual trigger**: Go to `Actions` → `Report Generation` → `Run workflow` → `Run now`

### Cloud RAG Endpoint and Asset Sync

The technology alternatives page uses browser-side keyword filtering for quick narrowing, then calls the Cloudflare Worker in `rag_engine/` for cloud RAG prioritization. CI builds a RAG asset manifest from `reports/`, `data/processed/`, and `frontend/data/`, uploads those assets to Cloudflare R2 when configured, and the Worker retrieves report/data evidence from that bucket.

Set these repository secrets for Cloudflare RAG:

- `CLOUD_RAG_ENDPOINT`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_R2_BUCKET` (current Worker binding expects `auto-rag`)
- Optional S3 API upload secrets: `CLOUDFLARE_R2_S3_ENDPOINT`, `CLOUDFLARE_R2_S3_ACCESS_KEY_ID`, `CLOUDFLARE_R2_S3_SECRET_ACCESS_KEY`

Alternatively, the same self-developed RAG engine can run on Hugging Face Spaces as a Docker Space using the files in `rag_engine/`. Set `HF_TOKEN` and `HF_SPACE_ID` to let CI upload the Docker Space. Hugging Face's default CPU Basic Space is currently free and provides 2 vCPU, 16 GB RAM, and 50 GB non-persistent disk. The Space endpoint can also be used as `CLOUD_RAG_ENDPOINT`.

### Cloudflare DNS for GitHub Pages

DNS records cannot point to a URL path. In Cloudflare DNS, do not set a CNAME target such as `dennislee928.github.io/pbx_estimation`; the `/pbx_estimation` part is a path, not a hostname.

For a custom subdomain such as `mtk-pbx-estimation.example.com`, set:

- Type: `CNAME`
- Name: `mtk-pbx-estimation`
- Target/content: `dennislee928.github.io`

Then set GitHub repository variables:

- `PAGES_CUSTOM_DOMAIN=mtk-pbx-estimation.example.com`
- Optional override: `NEXT_PUBLIC_SITE_BASE_PATH=/`

When `PAGES_CUSTOM_DOMAIN` is set and `NEXT_PUBLIC_SITE_BASE_PATH` is blank, the workflow automatically builds frontend assets for root-domain hosting. Keep `NEXT_PUBLIC_SITE_BASE_PATH=/pbx_estimation` only when you explicitly want the default `https://dennislee928.github.io/pbx_estimation/` URL.

See `docs/cloudflare_pages_dns.md` for the exact Cloudflare DNS records.

The endpoint returns:

```json
{
  "recommendation": "short explanation",
  "alternatives": [{ "name": "MQTT (MQTT-SN)", "rank": 1, "reason": "why it fits" }],
  "solutions": [{ "name": "Twilio Programmable Voice", "rank": 1, "reason": "why it fits" }],
  "documents": [{ "name": "reports/global_research_report_zh.md", "rank": 1, "excerpt": "retrieved report/data evidence" }]
}
```

### NotebookLM

Google NotebookLM does not have an official public file-upload API. CI therefore creates a NotebookLM-ready bundle at `rag_engine/dist/notebooklm_sources/` and includes it in the workflow artifact for manual upload. If you run an unofficial bridge such as `notebooklm-rest-api` or `notebooklm-py`, set `NOTEBOOKLM_UPLOAD_URL` and optionally `NOTEBOOKLM_API_TOKEN`; CI will post the selected sources to that endpoint.

### How to Fill `.env.example`

Copy `.env.example` to `.env` for local work, and add the same names as GitHub repository secrets when CI needs them.

| Variable | How to get the value |
|----------|----------------------|
| `NEXT_PUBLIC_CLOUD_RAG_ENDPOINT` | Public RAG endpoint used by the frontend build. Use either your Cloudflare Worker URL, for example `https://pbxanalyze.pcleegood.workers.dev/`, or your Hugging Face Space URL, for example `https://<user>-pbx-rag-engine.hf.space/`. |
| `CLOUD_RAG_ENDPOINT` | Same endpoint as above, stored as a GitHub secret so `.github/workflows/report.yml` can pass it into `NEXT_PUBLIC_CLOUD_RAG_ENDPOINT` during the Pages build. |
| `NEXT_PUBLIC_SITE_BASE_PATH` | Optional GitHub repository variable. Leave blank when `PAGES_CUSTOM_DOMAIN` is set; the workflow will use `/`. Use `/pbx_estimation` only for the default GitHub Pages project URL. |
| `PAGES_CUSTOM_DOMAIN` | GitHub repository variable. Set to the custom domain hostname only, for example `mtk-pbx-estimation.example.com`; do not include `https://` or `/pbx_estimation`. |
| `RAG_ASSET_PREFIX` | Usually `latest`. Change only if you want separate R2/Hugging Face asset namespaces such as `staging` or a dated prefix. |
| `CLOUDFLARE_API_TOKEN` | Cloudflare R2 Account API Token, for example your `pbx_application_token`. This is used by Wrangler remote upload. It is not the same as an R2 S3 Access Key ID. |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Dashboard → select account → account ID in the dashboard/API Tokens page, or run `npx wrangler whoami` after login. |
| `CLOUDFLARE_R2_BUCKET` | Create an R2 bucket in Cloudflare Dashboard → R2. Current default: `auto-rag`. |
| `CLOUDFLARE_R2_S3_ENDPOINT` | Optional S3 API path. If you use only `pbx_application_token`, leave all S3 fields empty. For S3 API mode, use `https://8dfc8c4994bd0925c72ab9e2eff79b48.r2.cloudflarestorage.com/auto-rag`; CI strips the trailing `/auto-rag` when calling the S3 API. |
| `CLOUDFLARE_R2_S3_ACCESS_KEY_ID` | Cloudflare Dashboard → R2 → Manage R2 API Tokens → create an R2 token with object read/write access for the `auto-rag` bucket. Use the 32-character Access Key ID. Do not use the Cloudflare API token or token id here. |
| `CLOUDFLARE_R2_S3_SECRET_ACCESS_KEY` | Secret Access Key shown once when creating the R2 S3 API token. Store only as a local `.env` value or GitHub secret. |
| `HF_TOKEN` | Hugging Face → Settings → Access Tokens → create a token with write access to Spaces. Use this as a GitHub secret for CI deployment. |
| `HF_SPACE_ID` | Hugging Face Space repo id in `<username-or-org>/<space-name>` format, for example `dennis-lee/pbx-rag-engine`. Create it in the Hugging Face UI or let CI create it with `hf repos create ... --type space --space-sdk docker --exist-ok`. |
| `NOTEBOOKLM_UPLOAD_URL` | Optional. Only set this if you run an unofficial NotebookLM bridge such as `notebooklm-rest-api` or `notebooklm-py`. Use that bridge's upload endpoint URL. Leave empty for manual NotebookLM upload. |
| `NOTEBOOKLM_API_TOKEN` | Optional token required by your unofficial NotebookLM bridge, if any. Leave empty if the bridge does not require bearer auth. |
| `NOTEBOOKLM_TIMEOUT` | HTTP timeout in seconds for the optional NotebookLM bridge upload. Default: `60`. |
| `PORT` | Runtime port for the Hugging Face Docker Space/local server. Hugging Face Docker Spaces should use `7860`. |
| `HOST` | Runtime host bind address. Use `0.0.0.0` for Docker/Hugging Face Spaces. |
| `ALLOWED_ORIGINS` | CORS allowlist for the RAG engine. Use `*` for quick testing, or the GitHub Pages origin for production. |
| `HF_RAG_ASSET_ROOT` | Local asset directory inside the Hugging Face Docker container. Keep `/app/dist/hf_assets` unless you change the Dockerfile. |
| `USE_WORKERS_AI` | Cloudflare Worker setting. Use `true` to call Workers AI for the final summary, or `false` to use deterministic retrieval/ranking only. Hugging Face Docker Space uses deterministic mode. |

### Dependencies

`pandas`, `numpy`, `scipy`, `matplotlib`, `seaborn`, `wbgapi`, `lifelines`, `scikit-learn`, `pyyaml`, `requests`, `jupyter`, `nbconvert`, `papermill`

---

<a id="chinese"></a>

## 概述（中文）

多國 PBX 市場衰退與 VoIP 普及趨勢的量化預測專案，採用時間序列分析與存活分析模型。

### 問題

傳統 PBX 交換機正被 VoIP/雲端方案快速取代。本專案透過資料科學回答兩個核心問題：

1. **各國趨勢預測** — 各國傳統 PBX 市場何時消亡？（Logistic S 曲線模型）
2. **產品成功率評估** — 在萎縮市場推出新 PBX 網關產品的存活機率為何？（Cox 比例風險模型）

### 數學模型

#### 1. S 曲線（羅吉斯成長模型，又稱邏輯性成長模型）— 趨勢預測

$$P(t) = \frac{K}{1 + e^{-r(t - t_0)}}$$

使用 `scipy.optimize.curve_fit` 對每個國家獨立擬合，預測市場飽和點與消亡時間點。

#### 2. Cox 比例風險模型 — 產品存活分析

$$h(t|X) = h_0(t) \exp(\sum_{i=1}^n \beta_i X_i)$$

使用 `lifelines.CoxPHFitter`，共變量包含 PSTN 退場政策（BEREC 資料）、寬頻普及率等。

### 資料來源

- **World Bank API** — 各國固定電話訂閱數歷年資料
- **ITU DataHub API** — ICT 指標（固網、寬頻、網際網路使用者）
- **BEREC**（歐洲監管機構聯盟）— 各國銅纜退場時程表（PDF 解析）
- **UK Parliament** — 英國 PSTN 關閉時間軸（Commons Library CBP-9471）
- **CEPT** — 歐洲 PSTN/ISDN 轉 IP 遷移報告（ECC Report 265）
- **NCC（台灣）** — 行動通信用戶統計、市話號碼核配（NCC API / 政府資料開放平臺）

### 使用方式

```bash
git clone https://github.com/dennis-lee/pbx_estimation.git
cd pbx_estimation
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
jupyter notebook notebooks/
```

### GitHub Actions 自動報告產出

透過 GitHub Actions 定期自動執行：

- **排程**：每小時 UTC 整點自動執行
- **手動觸發**：GitHub UI → Actions → Report Generation → Run workflow
- **流程**：抓取最新資料 → 依序執行所有 Notebook → 輸出 HTML/PDF 報告 → 產出可下載的 Artifact

### 雲端 RAG 端點與資產同步

技術替代方案頁面只在瀏覽器做快速關鍵字篩選，優先排序由 `rag_engine/` 的 Cloudflare Worker 回傳。CI 會將 `reports/`、`data/processed/`、`frontend/data/` 建成 RAG asset manifest，並在設定 Cloudflare secrets 後上傳到 Cloudflare R2 bucket，Worker 會從 bucket 讀取報告/資料證據。

需要的 repository secrets：`CLOUD_RAG_ENDPOINT`、`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`、`CLOUDFLARE_R2_BUCKET`。

也可以用 `rag_engine/` 的 Dockerfile 將同一套自研 RAG engine 部署到 Hugging Face Spaces。設定 `HF_TOKEN` 與 `HF_SPACE_ID` 後，CI 會上傳 Docker Space；Hugging Face CPU Basic Space 目前為免費方案，並提供 2 vCPU、16 GB RAM、50 GB 非持久磁碟。Space URL 也可作為 `CLOUD_RAG_ENDPOINT`。

### NotebookLM

Google NotebookLM 沒有官方公開檔案上傳 API。CI 會產生 `rag_engine/dist/notebooklm_sources/`，並放進 workflow artifact 供手動上傳。若你自行架設 `notebooklm-rest-api` 或 `notebooklm-py` 這類非官方橋接服務，可設定 `NOTEBOOKLM_UPLOAD_URL` 與選用的 `NOTEBOOKLM_API_TOKEN`，CI 會將來源檔 POST 到該端點。

### 如何填寫 `.env.example`

本機開發可將 `.env.example` 複製為 `.env`；CI 需要使用的值，請用同名 GitHub repository secrets 設定。

| 變數 | 取得方式 |
|------|----------|
| `NEXT_PUBLIC_CLOUD_RAG_ENDPOINT` / `CLOUD_RAG_ENDPOINT` | 使用 Cloudflare Worker URL 或 Hugging Face Space URL。前者給前端建置用，後者是 CI secret 名稱。 |
| `RAG_ASSET_PREFIX` | 通常維持 `latest`。只有要分 staging/date namespace 時才需要修改。 |
| `CLOUDFLARE_API_TOKEN` | Cloudflare R2 Account API Token，例如你的 `pbx_application_token`。這是給 Wrangler remote upload 用，不是 R2 S3 Access Key ID。 |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare 帳號頁面取得，或登入後執行 `npx wrangler whoami`。 |
| `CLOUDFLARE_R2_BUCKET` | Cloudflare R2 建立 bucket；目前預設 `auto-rag`。 |
| `CLOUDFLARE_R2_S3_ENDPOINT` | 選填的 S3 API 路徑。如果只使用 `pbx_application_token`，請讓所有 S3 欄位保持空白。若使用 S3 API 模式，你的 bucket 可填 `https://8dfc8c4994bd0925c72ab9e2eff79b48.r2.cloudflarestorage.com/auto-rag`。 |
| `CLOUDFLARE_R2_S3_ACCESS_KEY_ID` / `CLOUDFLARE_R2_S3_SECRET_ACCESS_KEY` | Cloudflare Dashboard → R2 → Manage R2 API Tokens 建立限定 `auto-rag` bucket 的讀寫 token；Access Key ID 是 32 字元，不是 Cloudflare API token 或 token id。secret key 只會顯示一次，放 GitHub secret。 |
| `HF_TOKEN` | Hugging Face Settings → Access Tokens 建立具 Spaces 寫入權限的 token。 |
| `HF_SPACE_ID` | Hugging Face Space repo id，格式 `<username-or-org>/<space-name>`。 |
| `NOTEBOOKLM_UPLOAD_URL` / `NOTEBOOKLM_API_TOKEN` | 只有使用非官方 NotebookLM bridge 時才填；手動上傳 NotebookLM 時保持空白。 |
| `NOTEBOOKLM_TIMEOUT` | NotebookLM bridge 上傳 timeout 秒數，預設 `60`。 |
| `PORT` / `HOST` | Docker/Hugging Face Spaces 使用 `7860` 與 `0.0.0.0`。 |
| `ALLOWED_ORIGINS` | RAG engine CORS 設定；測試可用 `*`，正式環境建議填 GitHub Pages origin。 |
| `HF_RAG_ASSET_ROOT` | Hugging Face Docker container 內的資產路徑，除非改 Dockerfile，維持 `/app/dist/hf_assets`。 |
| `USE_WORKERS_AI` | Cloudflare Worker 是否使用 Workers AI 產生摘要；Hugging Face Docker Space 使用 deterministic ranking。 |

---

## License

MIT

<!-- CICD_SUMMARY_START -->
## CI/CD Crawler Summary

_Last generated: 2026-07-11_

- 155 解決方案
- 42 國家/地區
- 131 替代技術
- 126 供應商

<!-- CICD_SUMMARY_END -->

