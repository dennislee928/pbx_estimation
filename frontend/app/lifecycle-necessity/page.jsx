"use client";

import { getLang } from "../../i18n";
import data from "../../data/lifecycle_necessity.json";

const L = getLang();
const en = L === "en";
const pick = (base) => data[`${base}_${en ? "en" : "zh"}`];

const CAT_LABELS = {
  cutting_edge: { en: "Cutting edge", zh: "前沿技術" },
  mature_active: { en: "Mature active", zh: "成熟活躍" },
  most_used_current: { en: "Current installed base", zh: "現行主流" },
  most_used_eol: { en: "EOL / legacy", zh: "已停產舊系統" },
};

export default function LifecycleNecessityPage() {
  const counts = data.lifecycle_counts || {};
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="research-page">
      <h2>{pick("title")}</h2>
      <p className="subtitle">{pick("method")}</p>

      {/* Hypothesis */}
      <div className="research-section">
        <h3>{en ? "Hypothesis" : "假設"}</h3>
        <p>
          {en
            ? `H₀: replacing is NOT necessary — EOL share p_eol ≤ ${data.null_p}. H₁: p_eol > ${data.null_p} (a majority of the installed base is obsolete). One-sided exact binomial test, α = ${data.alpha}.`
            : `H₀：汰換非必要——EOL 比例 p_eol ≤ ${data.null_p}；H₁：p_eol > ${data.null_p}（多數安裝基數已過時）。單尾精確二項檢定，α = ${data.alpha}。`}
        </p>
      </div>

      {/* Result */}
      <div className="research-section">
        <h3>{en ? "Test result" : "檢定結果"}</h3>
        <table className="comparison-table">
          <thead>
            <tr>
              <th>{en ? "Solutions (n)" : "方案數 (n)"}</th>
              <th>{en ? "EOL (k)" : "EOL (k)"}</th>
              <th>{en ? "EOL share" : "EOL 比例"}</th>
              <th>{en ? "95% CI" : "95% 信賴區間"}</th>
              <th>p</th>
              <th>{en ? "Verdict" : "判定"}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{data.n}</td>
              <td>{data.k_eol}</td>
              <td>{(data.p_hat * 100).toFixed(1)}%</td>
              <td>
                {(data.ci_low * 100).toFixed(1)}% … {(data.ci_high * 100).toFixed(1)}%
              </td>
              <td>{data.p_value.toFixed(3)}</td>
              <td>
                <span className={`maturity-badge ${data.reject_h0 ? "mainstream" : "frontier"}`}>
                  {pick("verdict")}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Lifecycle mix */}
      <div className="research-section">
        <h3>{en ? "Lifecycle mix of the installed base" : "安裝基數的生命週期分布"}</h3>
        {Object.entries(CAT_LABELS).map(([key, label]) => (
          <div className="bar-row" key={key}>
            <span>{en ? label.en : label.zh}</span>
            <div className="bar-track">
              <div style={{ width: `${((counts[key] || 0) / total) * 100}%` }} />
            </div>
            <strong>{counts[key] || 0}</strong>
          </div>
        ))}
      </div>

      {/* Sources */}
      <div className="research-section">
        <h3>{en ? "Data sources" : "資料來源"}</h3>
        <ul>
          {data.sources.map((s) => (
            <li key={s.url}>
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.name}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
