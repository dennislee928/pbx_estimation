"use client";

import { useState } from "react";
import { t } from "../i18n";
import Sidebar from "../components/Sidebar";
import ReportViewer from "../components/ReportViewer";

const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const NAV_ITEMS = [
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
    ],
  },
];

const FLAT_ITEMS = NAV_ITEMS.flatMap((g) => g.items);

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
          {isReport ? (
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
