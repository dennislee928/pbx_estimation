from __future__ import annotations

import json
import sys
from datetime import date
from html import escape
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.research.product_researcher import analyze_registry, summarize_registry
from src.research.solution_crawler import discover_solution_catalog
from src.research.tech_researcher import generate_awesome_list


PROCESSED = ROOT / "data" / "processed"
FRONTEND_DATA = ROOT / "frontend" / "data"
REPORTS = ROOT / "reports"
README = ROOT / "README.md"

SOURCES = [
    {
        "name": "Gartner UCaaS Magic Quadrant, published 2025-09-22",
        "url": "https://www.gartner.com/en/documents/6979866",
        "note_en": "Used to anchor current major UCaaS provider categories and AI/UCaaS market framing.",
        "note_zh": "用於校準現行主要 UCaaS 供應商分類與 AI/UCaaS 市場脈絡。",
    },
    {
        "name": "Microsoft Teams Phone official product page",
        "url": "https://www.microsoft.com/en-us/microsoft-teams/microsoft-teams-phone",
        "note_en": "Confirms cloud phone, PSTN calling, Operator Connect/Direct Routing, SLA, and AI call features.",
        "note_zh": "確認雲端電話、PSTN 通話、Operator Connect/Direct Routing、SLA 與 AI 通話功能。",
    },
    {
        "name": "Twilio Programmable Voice documentation and 2026 platform announcement",
        "url": "https://www.twilio.com/docs/voice",
        "note_en": "Anchors API-first voice, real-time voice, and agentic communications patterns.",
        "note_zh": "用於校準 API-first 語音、即時語音與代理式通訊模式。",
    },
    {
        "name": "Zoom Phone official product page",
        "url": "https://www.zoom.com/en/products/voip-phone/",
        "note_en": "Confirms Zoom Phone as a cloud VoIP system with AI-assisted call workflows.",
        "note_zh": "確認 Zoom Phone 為雲端 VoIP 電話系統並具備 AI 輔助通話流程。",
    },
    {
        "name": "3CX V20 release notes",
        "url": "https://www.3cx.com/blog/releases/v20-final/",
        "note_en": "Anchors active mature software PBX lifecycle status.",
        "note_zh": "用於校準成熟且仍活躍的軟體 PBX 生命週期狀態。",
    },
]

CRAWLER_TAXONOMY = [
    "UCaaS / cloud PBX",
    "CCaaS / contact-center voice",
    "CPaaS / programmable voice API",
    "Open-source and self-hosted PBX",
    "Regional telco hosted PBX and SIP voice",
    "IoT SIM, eSIM, cellular connectivity",
    "Industrial SCADA/PLC/building control",
    "Non-IP physical, electrical, optical, acoustic, mechanical, pneumatic, hydraulic, and workflow triggers",
    "Wireless/radio/satellite/cellular alternatives",
    "Serial, wired, relay, dry-contact, access-control, AV, and building-bus triggers",
]


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.fillna("").to_json(orient="records"))


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _crawler_context(registry: pd.DataFrame, awesome: pd.DataFrame) -> dict:
    """Summarize current known options before the crawler/discovery stage expands them."""
    return {
        "known_solution_count": int(len(registry)),
        "known_country_region_count": int(registry["country_code"].nunique()),
        "known_alternative_count": int(len(awesome)),
        "known_vendor_count": int(registry["vendor"].nunique()),
        "existing_solution_names": sorted(registry["name"].dropna().astype(str).unique().tolist()),
        "existing_alternative_names": sorted(awesome["name"].dropna().astype(str).unique().tolist()),
        "crawler_instruction": "Use these existing solutions and alternatives as seed knowledge, then search without category boundaries for additional PBX/UCaaS/CPaaS/eSIM/IoT/non-PSTN options not already listed. Expand especially beyond RF into wired, optical, acoustic, mechanical, pneumatic, hydraulic, human workflow, document, visual-code, industrial, building, security, AV, and edge-control triggers.",
        "expansion_queries": [
            "new UCaaS cloud PBX providers by country official",
            "programmable voice API CPaaS providers official docs",
            "IoT eSIM cellular connectivity platform edge device command official",
            "PSTN replacement alarm line IP gateway official",
            "industrial building automation PBX event relay alternatives official",
            "non RF non IP physical trigger alternatives relay optical acoustic pneumatic hydraulic official",
            "building automation access control dry contact OSDP Wiegand KNX DALI DMX official",
            "barcode QR USB HID scanner workflow trigger edge controller official",
            "industrial actuator pneumatic hydraulic solenoid PLC control official",
            "audio optical visual signal sensor trigger legacy equipment official",
            "fire alarm nurse call elevator auxiliary relay dry contact interface official",
            "AV control MIDI HDMI CEC infrared trigger command official",
            "manual SOP paper ticket scan to trigger workflow official",
        ],
    }


def _update_readme_summary(registry: pd.DataFrame, awesome: pd.DataFrame) -> None:
    start = "<!-- CICD_SUMMARY_START -->"
    end = "<!-- CICD_SUMMARY_END -->"
    today = date.today().isoformat()
    summary = "\n".join(
        [
            start,
            "## CI/CD Crawler Summary",
            "",
            f"_Last generated: {today}_",
            "",
            f"- {len(registry)} 解決方案",
            f"- {registry['country_code'].nunique()} 國家/地區",
            f"- {len(awesome)} 替代技術",
            f"- {registry['vendor'].nunique()} 供應商",
            "",
            end,
        ]
    )
    text = README.read_text() if README.exists() else ""
    if start in text and end in text:
        before = text.split(start, 1)[0].rstrip()
        after = text.split(end, 1)[1].lstrip()
        README.write_text(f"{before}\n\n{summary}\n\n{after}")
    else:
        README.write_text(f"{text.rstrip()}\n\n{summary}\n")


def _category_label(category: str, lang: str) -> str:
    labels = {
        "cutting_edge": ("Cutting edge / newest", "前沿 / 最新"),
        "mature_active": ("Mature active", "成熟且仍活躍"),
        "most_used_current": ("Major current installed base", "主流現行裝機"),
        "most_used_eol": ("Major EOL / legacy", "主流已停產 / 舊系統"),
    }
    return labels.get(category, (category, category))[0 if lang == "en" else 1]


def _continent_label(continent: str, lang: str) -> str:
    labels = {
        "asia_pacific": ("Asia-Pacific", "亞太"),
        "europe": ("Europe", "歐洲"),
        "americas": ("Americas", "美洲"),
        "middle_east": ("Middle East", "中東"),
        "africa": ("Africa", "非洲"),
    }
    return labels.get(continent, (continent, continent))[0 if lang == "en" else 1]


def _html_table(df: pd.DataFrame, columns: list[str], lang: str) -> str:
    labels = {
        "continent": ("Continent", "洲別"),
        "country_code": ("Country/region", "國家/地區"),
        "name": ("Name", "名稱"),
        "vendor": ("Vendor", "供應商"),
        "lifecycle_assigned": ("Lifecycle", "生命週期"),
        "recommended_terminals": ("Recommended terminals", "建議終端數"),
        "recommended_devices": ("Recommended terminals/devices", "建議終端/裝置數"),
        "cost_band": ("Cost band", "成本區間"),
        "cost_model": ("Cost model", "成本模式"),
        "industry_fit": ("Industry fit", "適用產業"),
        "resource_url": ("Source", "來源"),
        "pros": ("Pros", "優點"),
        "cons": ("Cons", "缺點"),
        "category": ("Category", "類別"),
        "medium": ("Medium", "媒介"),
        "latency": ("Latency", "延遲"),
        "security": ("Security", "安全性"),
    }
    header = "".join(
        f"<th>{escape(labels.get(c, (c, c))[0 if lang == 'en' else 1])}</th>"
        for c in columns
    )
    rows = []
    for _, row in df.iterrows():
        cells = []
        for col in columns:
            value = row.get(col, "")
            if col == "lifecycle_assigned":
                value = _category_label(str(value), lang)
            if col in {"resource_url", "url"} and value:
                safe_url = escape(str(value), quote=True)
                value = f'<a href="{safe_url}">official/source</a>'
                cells.append(f"<td>{value}</td>")
            else:
                cells.append(f"<td>{escape(str(value))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _build_report(lang: str, registry: pd.DataFrame, awesome: pd.DataFrame) -> tuple[str, str]:
    zh = lang == "zh"
    today = date.today().isoformat()
    title = "PBX Estimation Global Research Report" if not zh else "PBX Estimation 全球研究報告"
    subtitle = (
        "Global PBX/UCaaS vendor landscape, lifecycle classification, PSTN-alternative technology catalog, and deployment outputs."
        if not zh
        else "全球 PBX/UCaaS 供應商格局、生命週期分類、PSTN 替代技術清單與部署輸出。"
    )
    lifecycle = registry["lifecycle_assigned"].value_counts().reindex(
        ["cutting_edge", "mature_active", "most_used_current", "most_used_eol"], fill_value=0
    )
    continent = registry.groupby("continent")["name"].count().sort_values(ascending=False)
    tech_category = awesome["category"].value_counts()
    summary = summarize_registry(registry)

    md = [
        f"# {title}",
        "",
        f"_Generated: {today}_",
        "",
        subtitle,
        "",
        "## Executive Summary" if not zh else "## 執行摘要",
        "",
        (
            f"- Covered {len(registry)} PBX/VoIP/UCaaS solutions across {registry['country_code'].nunique()} countries/regions and {registry['continent'].nunique()} continent groups."
            if not zh
            else f"- 涵蓋 {len(registry)} 個 PBX/VoIP/UCaaS 方案，分布於 {registry['country_code'].nunique()} 個國家/地區與 {registry['continent'].nunique()} 個洲別群組。"
        ),
        (
            f"- Built {len(awesome)} PSTN alternatives spanning API, IP, brokered messaging, industrial, wireless, cellular, satellite, serial, dry-contact, optical, acoustic, mechanical, pneumatic, hydraulic, visual-code, and human-workflow solutions."
            if not zh
            else f"- 建立 {len(awesome)} 種 PSTN 替代方案，涵蓋 API、IP、訊息佇列、工業、無線、蜂巢、衛星、序列匯流排、乾接點、光學、聲學、機械、氣壓、液壓、視覺碼與人工流程方案。"
        ),
        (
            "- Current market direction is cloud/API/AI voice for new deployments, while hybrid PBX and TDM platforms remain material migration risks in installed bases."
            if not zh
            else "- 新部署方向明顯轉向雲端/API/AI 語音，但混合式 PBX 與 TDM 平台仍是既有裝機的主要遷移風險。"
        ),
        "",
        "## Crawler Coverage" if not zh else "## 爬蟲覆蓋分類",
        "",
    ]
    for item in CRAWLER_TAXONOMY:
        md.append(f"- {item}")
    md.extend([
        "",
        "## Lifecycle Counts" if not zh else "## 生命週期統計",
        "",
    ])
    for category, count in lifecycle.items():
        md.append(f"- {_category_label(category, lang)}: {int(count)}")
    md.extend(["", "## Continent Coverage" if not zh else "## 洲別覆蓋", ""])
    for name, count in continent.items():
        md.append(f"- {_continent_label(str(name), lang)}: {int(count)}")
    md.extend(["", "## Technology Alternatives" if not zh else "## 技術替代方案", ""])
    for name, count in tech_category.items():
        label = "Web/API/IP" if name == "web" else "Non-network/physical/industrial/RF"
        if zh:
            label = "網路/API/IP" if name == "web" else "非網路/實體媒介/工業/RF"
        md.append(f"- {label}: {int(count)}")
    md.extend(["", "## Sources" if not zh else "## 來源", ""])
    for source in SOURCES:
        note = source["note_en"] if not zh else source["note_zh"]
        md.append(f"- [{source['name']}]({source['url']}) - {note}")
    md_text = "\n".join(md) + "\n"

    top_registry = registry.sort_values(["continent", "country_code", "lifecycle_assigned", "name"]).head(120)
    top_awesome = awesome.sort_values(["category", "medium", "name"])
    html = f"""<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; color: #1f2937; background: #f7f8fb; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 56px; }}
    h1 {{ margin: 0 0 8px; font-size: 2rem; }}
    h2 {{ margin-top: 32px; }}
    .meta {{ color: #64748b; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 20px 0; }}
    .card {{ background: white; border: 1px solid #dbe3ef; border-radius: 8px; padding: 14px; }}
    .metric {{ font-size: 1.8rem; font-weight: 700; color: #0f766e; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #dbe3ef; margin: 12px 0 28px; font-size: 0.86rem; }}
    th, td {{ border-bottom: 1px solid #edf2f7; text-align: left; padding: 9px; vertical-align: top; }}
    th {{ background: #eaf1f8; }}
    a {{ color: #075985; }}
  </style>
</head>
<body>
<main>
  <h1>{escape(title)}</h1>
  <p class="meta">{escape(subtitle)} {escape(today)}</p>
  <section class="grid">
    <div class="card"><div class="metric">{len(registry)}</div><div>{"Solutions" if not zh else "方案"}</div></div>
    <div class="card"><div class="metric">{registry['country_code'].nunique()}</div><div>{"Countries/regions" if not zh else "國家/地區"}</div></div>
    <div class="card"><div class="metric">{len(awesome)}</div><div>{"PSTN alternatives" if not zh else "PSTN 替代方案"}</div></div>
    <div class="card"><div class="metric">{registry['vendor'].nunique()}</div><div>{"Vendors" if not zh else "供應商"}</div></div>
  </section>
  <h2>{"Crawler Coverage" if not zh else "爬蟲覆蓋分類"}</h2>
  <ul>
    {''.join(f'<li>{escape(item)}</li>' for item in CRAWLER_TAXONOMY)}
  </ul>
  <h2>{"Lifecycle Summary" if not zh else "生命週期摘要"}</h2>
  {_html_table(summary, ["continent", "lifecycle_assigned", "count", "vendors"], lang)}
  <h2>{"Solution Registry" if not zh else "方案清單"}</h2>
  {_html_table(top_registry, ["continent", "country_code", "name", "vendor", "lifecycle_assigned", "recommended_terminals", "cost_band", "industry_fit", "resource_url", "pros", "cons"], lang)}
  <h2>{"PSTN Alternatives Awesome List" if not zh else "PSTN 替代方案 Awesome List"}</h2>
  {_html_table(top_awesome, ["name", "category", "medium", "recommended_devices", "cost_model", "industry_fit", "resource_url", "latency", "security", "pros", "cons"], lang)}
  <h2>{"Sources" if not zh else "來源"}</h2>
  <ul>
    {''.join(f'<li><a href="{escape(s["url"])}">{escape(s["name"])}</a> - {escape(s["note_zh"] if zh else s["note_en"])}</li>' for s in SOURCES)}
  </ul>
</main>
</body>
</html>
"""
    return md_text, html


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    FRONTEND_DATA.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    registry = analyze_registry(output_path=str(PROCESSED / "solution_registry.csv"))
    awesome = generate_awesome_list(output_path=str(PROCESSED / "awesome_list.csv"))

    _write_json(FRONTEND_DATA / "solution_registry.json", _records(registry))
    _write_json(FRONTEND_DATA / "awesome_list.json", _records(awesome))
    _write_json(FRONTEND_DATA / "crawler_seed_context.json", _crawler_context(registry, awesome))
    _write_json(FRONTEND_DATA / "crawler_discoveries.json", discover_solution_catalog())
    _write_json(FRONTEND_DATA / "crawler_taxonomy.json", CRAWLER_TAXONOMY)
    _write_json(FRONTEND_DATA / "research_sources.json", SOURCES)
    _update_readme_summary(registry, awesome)

    for lang in ("en", "zh"):
        md, html = _build_report(lang, registry, awesome)
        (REPORTS / f"global_research_report_{lang}.md").write_text(md)
        (REPORTS / f"global_research_report_{lang}.html").write_text(html)

    index = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PBX Estimation</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans TC", sans-serif; background: #f4f6f8; color: #172033; }}
    main {{ min-height: 100vh; display: grid; place-items: center; padding: 24px; }}
    section {{ width: min(920px, 100%); background: white; border: 1px solid #dbe3ea; border-radius: 8px; padding: 34px; }}
    h1 {{ margin: 0 0 12px; font-size: 2rem; }}
    p {{ color: #52606d; line-height: 1.6; max-width: 760px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 22px 0; }}
    .metric {{ border: 1px solid #e4e9ef; border-radius: 8px; padding: 14px; }}
    .metric strong {{ display: block; font-size: 1.7rem; color: #0f766e; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    a {{ color: #0f766e; font-weight: 700; text-decoration: none; border: 1px solid #b8c7d3; border-radius: 6px; padding: 10px 12px; }}
    a.primary {{ background: #0f766e; color: white; border-color: #0f766e; }}
  </style>
</head>
<body>
<main>
  <section>
    <h1>PBX Estimation</h1>
    <p>Global PBX, UCaaS, CPaaS, eSIM/IoT, and non-PSTN trigger alternatives. 全球 PBX、UCaaS、CPaaS、eSIM/IoT 與非 PSTN 觸發替代方案研究。</p>
    <div class="metrics">
      <div class="metric"><strong>{len(registry)}</strong><span>Solutions / 解決方案</span></div>
      <div class="metric"><strong>{registry['country_code'].nunique()}</strong><span>Countries / 國家地區</span></div>
      <div class="metric"><strong>{len(awesome)}</strong><span>Alternatives / 替代技術</span></div>
      <div class="metric"><strong>{registry['vendor'].nunique()}</strong><span>Vendors / 供應商</span></div>
    </div>
    <div class="actions">
      <a class="primary" href="zh/">繁體中文網站</a>
      <a href="en/">English Site</a>
      <a href="reports/global_research_report_zh.html">中文研究報告</a>
      <a href="reports/global_research_report_en.html">English Report</a>
    </div>
  </section>
</main>
</body>
</html>"""
    (REPORTS / "index.html").write_text(index)


if __name__ == "__main__":
    main()
