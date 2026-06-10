"use client";

import { useState } from "react";
import { t, getLang } from "../i18n";
import Sidebar from "../components/Sidebar";
import ReportViewer from "../components/ReportViewer";
import registry from "../data/solution_registry.json";
import alternatives from "../data/awesome_list.json";

const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const L = getLang();

const categoryLabels = {
  cutting_edge: L === "en" ? "Cutting edge" : "前沿技術",
  mature_active: L === "en" ? "Mature active" : "成熟活躍",
  most_used_current: L === "en" ? "Current installed base" : "現行主流",
  most_used_eol: L === "en" ? "EOL / legacy" : "已停產舊系統",
};

function countBy(rows, key) {
  return rows.reduce((acc, row) => {
    const value = row[key] || "unknown";
    acc[value] = (acc[value] || 0) + 1;
    return acc;
  }, {});
}

const lifecycleCounts = countBy(registry, "lifecycle_assigned");
const continentCounts = countBy(registry, "continent");
const highlighted = registry
  .filter((row) => /esim|iot|api|ucaas|cloud/i.test(`${row.tags} ${row.description}`))
  .slice(0, 10);

const NAV_ITEMS = [
  {
    section: "overview",
    items: [{ id: "overview", label: t("executiveView"), page: "overview" }],
  },
  {
    section: "reports",
    items: [
      { id: "01_fetch_data", label: t("report01"), file: `${BASE}/reports/01_fetch_data.html` },
      { id: "02_eda_visualization", label: t("report02"), file: `${BASE}/reports/02_eda_visualization.html` },
      { id: "03_logistic_growth", label: t("report03"), file: `${BASE}/reports/03_logistic_growth.html` },
      { id: "04_survival_analysis", label: t("report04"), file: `${BASE}/reports/04_survival_analysis.html` },
      { id: "06_product_research", label: t("report06"), file: `${BASE}/reports/06_product_research.html` },
      { id: "07_tech_alternatives", label: t("report07"), file: `${BASE}/reports/07_tech_alternatives.html` },
    ],
  },
  {
    section: "research",
    items: [
      { id: "market_brief", label: t("marketBrief"), page: "market-brief" },
      { id: "product_research", label: t("productResearch"), page: "product-research" },
      { id: "tech_alternatives", label: t("techAlternatives"), page: "tech-alternatives" },
      { id: "sim_technologies", label: t("simTechnologies"), page: "sim-technologies" },
    ],
  },
];

const FLAT_ITEMS = NAV_ITEMS.flatMap((g) => g.items);

function Metric({ label, value }) {
  return (
    <div className="metric-tile">
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}

function Overview({ onSelect }) {
  const countryCount = new Set(registry.map((row) => row.country_code)).size;
  const vendorCount = new Set(registry.map((row) => row.vendor)).size;
  return (
    <div className="overview-page">
      <section className="overview-hero">
        <div>
          <p className="eyebrow">PBX Estimation</p>
          <h2>{L === "en" ? "Global PBX, UCaaS, API voice, and edge-trigger alternatives" : "全球 PBX、UCaaS、API 語音與邊緣觸發替代方案"}</h2>
          <p>
            {L === "en"
              ? "A bilingual research workspace for comparing current, mature, and legacy voice platforms with non-PSTN command paths, source URLs, sizing guidance, cost bands, and industry fit."
              : "雙語研究工作台，用於比較現行、成熟與舊式語音平台，並納入非 PSTN 控制路徑、來源網址、建議規模、成本區間與適用產業。"}
          </p>
        </div>
        <div className="hero-actions">
          <button onClick={() => onSelect("product_research")}>{t("solutions")}</button>
          <button onClick={() => onSelect("tech_alternatives")}>{t("alternatives")}</button>
          <button onClick={() => onSelect("06_product_research")}>{t("openReport")}</button>
        </div>
      </section>

      <section className="metric-grid">
        <Metric label={t("solutions")} value={registry.length} />
        <Metric label={t("countries")} value={countryCount} />
        <Metric label={t("alternatives")} value={alternatives.length} />
        <Metric label={t("vendors")} value={vendorCount} />
      </section>

      <section className="dashboard-grid">
        <div className="dashboard-panel">
          <h3>{t("lifecycleMix")}</h3>
          {Object.entries(categoryLabels).map(([key, label]) => (
            <div className="bar-row" key={key}>
              <span>{label}</span>
              <div className="bar-track">
                <div style={{ width: `${((lifecycleCounts[key] || 0) / registry.length) * 100}%` }} />
              </div>
              <strong>{lifecycleCounts[key] || 0}</strong>
            </div>
          ))}
        </div>
        <div className="dashboard-panel">
          <h3>{t("continentCoverage")}</h3>
          {Object.entries(continentCounts)
            .sort((a, b) => b[1] - a[1])
            .map(([continent, count]) => (
              <div className="coverage-row" key={continent}>
                <span>{continent.replace("_", " ")}</span>
                <strong>{count}</strong>
              </div>
            ))}
        </div>
      </section>

      <section className="dashboard-panel">
        <h3>{t("priorityOptions")}</h3>
        <div className="solution-list">
          {highlighted.map((row) => (
            <a className="solution-row" href={row.resource_url || "#"} key={`${row.vendor}-${row.name}`}>
              <span>
                <strong>{row.name}</strong>
                <small>{row.vendor} · {String(row.country_code).toUpperCase()} · {row.recommended_terminals}</small>
              </span>
              <span>{row.cost_band}</span>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}

export default function Home() {
  const [activeId, setActiveId] = useState(FLAT_ITEMS[0].id);
  const current = FLAT_ITEMS.find((i) => i.id === activeId);
  const isReport = current && "file" in current;

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>{t("siteTitle")}</h1>
      </header>
      <div className="app-body">
        <Sidebar groups={NAV_ITEMS} active={activeId} onSelect={setActiveId} />
        <main className="app-content">
          {current?.page === "overview" ? (
            <Overview onSelect={setActiveId} />
          ) : isReport ? (
            <ReportViewer report={current} />
          ) : current?.page === "market-brief" ? (
            <iframe className="report-frame" src={`${BASE}/market-brief`} title={current.label} />
          ) : (
            <iframe
              className="report-frame"
              src={`${BASE}/${current?.page}`}
              title={current?.label}
            />
          )}
        </main>
      </div>
    </div>
  );
}
