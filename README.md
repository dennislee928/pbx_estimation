# PBX Market Estimation & VoIP Trend Forecasting

[![Report Generation](https://github.com/dennis-lee/pbx_estimation/actions/workflows/report.yml/badge.svg)](https://github.com/dennis-lee/pbx_estimation/actions/workflows/report.yml)

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
| **ITU ICT Indicators** | IP communication share, infrastructure scores | CSV / API |
| **BEREC** (European Regulators) | Copper switch-off dates per country | PDF scraping (Table 3) |
| **UK House of Commons Library** | UK PSTN switch-off timeline | Structured web |
| **CEPT** | European IP migration status | Reports |
| **NCC (Taiwan)** | Local telecom statistics | Reports |

### Project Structure

```
pbx_estimation/
├── data/
│   ├── raw/          # API downloads cache
│   └── processed/    # Cleaned panel data
├── notebooks/
│   ├── 01_fetch_data.ipynb           # Data collection
│   ├── 02_eda_visualization.ipynb    # Exploratory analysis
│   ├── 03_logistic_growth.ipynb      # S-Curve fitting
│   └── 04_survival_analysis.ipynb    # CoxPH model
├── src/
│   ├── data/fetcher.py
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
- `CLOUDFLARE_R2_BUCKET` (default Worker binding expects `pbx-rag-assets`)

Alternatively, the same self-developed RAG engine can run on Hugging Face Spaces as a Docker Space using the files in `rag_engine/`. Set `HF_TOKEN` and `HF_SPACE_ID` to let CI upload the Docker Space. Hugging Face's default CPU Basic Space is currently free and provides 2 vCPU, 16 GB RAM, and 50 GB non-persistent disk. The Space endpoint can also be used as `CLOUD_RAG_ENDPOINT`.

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
- **ITU ICT 指標** — 通訊基礎建設轉型數據
- **BEREC**（歐洲監管機構聯盟）— 各國銅纜退場時程表（最權威來源）
- **UK Parliament** — 英國 PSTN 關閉時間軸 (2027.01)
- **NCC（台灣）** — 國內電信統計

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

---

## License

MIT

<!-- CICD_SUMMARY_START -->
## CI/CD Crawler Summary

_Last generated: 2026-06-04_

- 156 解決方案
- 42 國家/地區
- 106 替代技術
- 126 供應商

<!-- CICD_SUMMARY_END -->
