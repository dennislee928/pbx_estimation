import { useState } from "react";
import Sidebar from "./components/Sidebar";
import ReportViewer from "./components/ReportViewer";
import "./App.css";

const reports = [
  { id: "01_fetch_data", label: "資料擷取", file: "reports/01_fetch_data.html" },
  { id: "02_eda_visualization", label: "探索式資料分析與視覺化", file: "reports/02_eda_visualization.html" },
  { id: "03_logistic_growth", label: "邏輯成長模型", file: "reports/03_logistic_growth.html" },
  { id: "04_survival_analysis", label: "存活分析", file: "reports/04_survival_analysis.html" },
];

export default function App() {
  const [active, setActive] = useState(reports[0].id);
  const current = reports.find((r) => r.id === active);

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>PBX 市場預測與 VoIP 趨勢分析</h1>
      </header>
      <div className="app-body">
        <Sidebar reports={reports} active={active} onSelect={setActive} />
        <main className="app-content">
          {current && <ReportViewer report={current} />}
        </main>
      </div>
    </div>
  );
}
