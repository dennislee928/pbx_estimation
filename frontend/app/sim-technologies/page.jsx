"use client";

import { t, getLang } from "../../i18n";
import techs from "../../data/sim_technologies.json";
import comparison from "../../data/sim_comparison.json";

const L = getLang();

const MATURITY = {
  mainstream: { en: "Mainstream", zh: "主流採用" },
  emerging: { en: "Emerging", zh: "新興" },
  frontier: { en: "Frontier", zh: "前沿" },
  standard: { en: "Standard / Spec", zh: "標準 / 規範" },
};

// Evolution ladder from removable hardware toward fully software-defined identity.
const LADDER = [
  { en: "Removable SIM", zh: "可插拔 SIM" },
  { en: "eSIM (embedded)", zh: "eSIM（嵌入式）" },
  { en: "iSIM (integrated)", zh: "iSIM（整合式）" },
  { en: "SoftSIM (software)", zh: "SoftSIM（軟體）" },
];

function pick(row, base) {
  return L === "en" ? row[`${base}_en`] : row[`${base}_zh`];
}

export default function SimTechnologiesPage() {
  const specCount = techs.filter((x) => x.maturity === "standard").length;
  return (
    <div className="research-page">
      <h2>{L === "en" ? "SIM & Cellular Connectivity Evolution" : "SIM 與行動連接演進"}</h2>
      <p className="subtitle">
        {L === "en"
          ? `How embedded identity is moving from removable cards to fully software-defined SIMs — and why it matters for SIM-bearer PBX, UCaaS, and IoT voice endpoints. ${techs.length} technologies and specifications, including ${specCount} GSMA standards.`
          : `嵌入式身分如何從可插拔卡片走向完全軟體定義的 SIM——以及這對 SIM 承載的 PBX、UCaaS 與 IoT 語音端點的意義。涵蓋 ${techs.length} 項技術與規範，包含 ${specCount} 項 GSMA 標準。`}
      </p>

      <div className="research-section">
        <h3>{L === "en" ? "De-hardwaring Ladder" : "去硬體化階梯"}</h3>
        <p>
          {L === "en"
            ? "Each rung removes hardware dependency and board space while pushing provisioning further into software and the cloud."
            : "每一階都在移除硬體依賴與板上空間，並將配置進一步推向軟體與雲端。"}
        </p>
        <div className="sim-ladder">
          {LADDER.map((step, i) => (
            <div className="sim-ladder-step" key={i}>
              <span className="sim-ladder-index">{i + 1}</span>
              <span>{L === "en" ? step.en : step.zh}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="research-section">
        <h3>{L === "en" ? "Technology & Specification Cards" : "技術與規範卡片"}</h3>
        <div className="sim-card-grid">
          {techs.map((row) => {
            const m = MATURITY[row.maturity] || MATURITY.emerging;
            return (
              <article className="sim-card" key={row.id}>
                <header className="sim-card-head">
                  <h4>{L === "en" ? row.name_en : row.name_zh}</h4>
                  <span className={`maturity-badge ${row.maturity}`}>{L === "en" ? m.en : m.zh}</span>
                </header>
                <p className="sim-form">{pick(row, "form_factor")}</p>
                <p>{pick(row, "summary")}</p>

                <dl className="sim-meta">
                  <div>
                    <dt>{L === "en" ? "Power" : "功耗"}</dt>
                    <dd>{row.power_en}</dd>
                  </div>
                  <div>
                    <dt>{L === "en" ? "Footprint" : "佔板面積"}</dt>
                    <dd>{row.footprint_mm2 == null ? "—" : `~${row.footprint_mm2} mm²`}</dd>
                  </div>
                  <div>
                    <dt>{L === "en" ? "Security" : "安全性"}</dt>
                    <dd>{pick(row, "security")}</dd>
                  </div>
                  <div>
                    <dt>{L === "en" ? "Adoption" : "採用狀態"}</dt>
                    <dd>{pick(row, "adoption")}</dd>
                  </div>
                </dl>

                <div className="sim-tags">
                  {row.tags.map((tag) => (
                    <span className="sim-tag" key={tag}>#{tag}</span>
                  ))}
                </div>

                <div className="sim-block">
                  <strong>{L === "en" ? "Specs" : "規範"}</strong>
                  <ul>
                    {row.specs.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>

                <div className="sim-block">
                  <strong>{L === "en" ? "Use cases" : "應用場景"}</strong>
                  <ul>
                    {(L === "en" ? row.use_cases_en : row.use_cases_zh).map((u) => (
                      <li key={u}>{u}</li>
                    ))}
                  </ul>
                </div>

                <p className="sim-pbx">
                  <strong>{L === "en" ? "PBX / voice relevance: " : "PBX / 語音關聯："}</strong>
                  {pick(row, "pbx_relevance")}
                </p>
              </article>
            );
          })}
        </div>
      </div>

      <div className="research-section">
        <h3>{L === "en" ? "Traditional vs SIM-Evolution Comparison" : "傳統 vs SIM 演進比較"}</h3>
        <p className="sim-note">{L === "en" ? comparison.baseline_note_en : comparison.baseline_note_zh}</p>
        <p className="subtitle" style={{ marginTop: 0 }}>
          {L === "en"
            ? "Derived in notebook 09 (sim_connectivity_analysis) and exported to the frontend — incumbents trade physical wiring / manual card swaps for remote, software-defined provisioning."
            : "由 notebook 09（sim_connectivity_analysis）推導並匯出至前端——既有方式以遠端、軟體定義配置取代實體佈線與手動換卡。"}
        </p>
        <table className="registry-table">
          <thead>
            <tr>
              <th>{L === "en" ? "Option" : "方案"}</th>
              <th>{L === "en" ? "Type" : "類型"}</th>
              <th>{L === "en" ? "Footprint" : "佔板面積"}</th>
              <th>{L === "en" ? "Power idx" : "功耗指數"}</th>
              <th>{L === "en" ? "BOM idx" : "BOM 指數"}</th>
              <th>{L === "en" ? "Provisioning" : "配置方式"}</th>
              <th>{L === "en" ? "Remote switch" : "遠端切換"}</th>
            </tr>
          </thead>
          <tbody>
            {comparison.rows.map((r) => (
              <tr key={r.option}>
                <td>{r.option}</td>
                <td>
                  <span className={`maturity-badge ${r.kind === "traditional" ? "standard" : "emerging"}`}>
                    {r.kind === "traditional" ? (L === "en" ? "Traditional" : "傳統") : (L === "en" ? "New" : "新")}
                  </span>
                </td>
                <td>{r.footprint_mm2 == null ? "—" : `~${r.footprint_mm2} mm²`}</td>
                <td>{r.power_index == null ? "—" : r.power_index}</td>
                <td>{r.bom_index == null ? "—" : r.bom_index}</td>
                <td>{r.provisioning}</td>
                <td>{r.remote_switchable ? "✓" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="research-section">
        <h3>{L === "en" ? "Comparison Matrix" : "比較矩陣"}</h3>
        <table className="registry-table">
          <thead>
            <tr>
              <th>{L === "en" ? "Technology" : "技術"}</th>
              <th>{L === "en" ? "Maturity" : "成熟度"}</th>
              <th>{L === "en" ? "Footprint" : "佔板面積"}</th>
              <th>{L === "en" ? "Power" : "功耗"}</th>
              <th>{L === "en" ? "Security" : "安全性"}</th>
            </tr>
          </thead>
          <tbody>
            {techs.map((row) => (
              <tr key={row.id}>
                <td>{L === "en" ? row.name_en : row.name_zh}</td>
                <td>
                  <span className={`maturity-badge ${row.maturity}`}>
                    {L === "en" ? (MATURITY[row.maturity] || {}).en : (MATURITY[row.maturity] || {}).zh}
                  </span>
                </td>
                <td>{row.footprint_mm2 == null ? "—" : `~${row.footprint_mm2} mm²`}</td>
                <td>{row.power_en}</td>
                <td>{pick(row, "security")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
