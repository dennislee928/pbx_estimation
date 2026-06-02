"use client";

import { useState } from "react";
import Sidebar from "../components/Sidebar";
import ReportViewer from "../components/ReportViewer";

// NEXT_PUBLIC_BASE_PATH is injected by next.config.mjs;
// empty string ensures relative paths work during local dev.
const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const REPORTS = [
  {
    id: "01_fetch_data",
    label: "資料擷取",
    file: `${BASE}/reports/01_fetch_data.html`,
  },
  {
    id: "02_eda_visualization",
    label: "探索式資料分析",
    file: `${BASE}/reports/02_eda_visualization.html`,
  },
  {
    id: "03_logistic_growth",
    label: "羅吉斯成長模型",
    file: `${BASE}/reports/03_logistic_growth.html`,
  },
  {
    id: "04_survival_analysis",
    label: "存活分析",
    file: `${BASE}/reports/04_survival_analysis.html`,
  },
];

export default function Home() {
  const [activeId, setActiveId] = useState(REPORTS[0].id);
  const current = REPORTS.find((r) => r.id === activeId);

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>PBX 市場預測與 VoIP 趨勢分析</h1>
      </header>
      <div className="app-body">
        <Sidebar reports={REPORTS} active={activeId} onSelect={setActiveId} />
        <main className="app-content">
          {current && <ReportViewer report={current} />}
        </main>
      </div>
    </div>
  );
}
