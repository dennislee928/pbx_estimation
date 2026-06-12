"use client";

import { getLang } from "../../i18n";
import data from "../../data/security_integration.json";

const L = getLang();
const en = L === "en";
const pick = (base) => data[`${base}_${en ? "en" : "zh"}`];

function LegRow({ label, leg }) {
  return (
    <tr>
      <td>{label}</td>
      <td>{leg.n}</td>
      <td>{leg.mean.toFixed(2)}</td>
      <td>
        {leg.direction === "greater" ? "> " : "< "}
        {leg.popmean}
      </td>
      <td>
        {leg.ci_low.toFixed(2)} … {leg.ci_high.toFixed(2)}
      </td>
      <td>{leg.p_value < 0.001 ? leg.p_value.toExponential(1) : leg.p_value.toFixed(3)}</td>
      <td>{leg.cohens_d.toFixed(2)}</td>
      <td>
        <span className={`maturity-badge ${leg.reject_h0 ? "mainstream" : "frontier"}`}>
          {leg.reject_h0 ? (en ? "Reject H₀" : "拒絕 H₀") : en ? "Fail to reject" : "未拒絕"}
        </span>
      </td>
    </tr>
  );
}

export default function SecurityIntegrationPage() {
  return (
    <div className="research-page">
      <h2>{pick("title")}</h2>
      <p className="subtitle">{pick("method")}</p>

      {/* Hypothesis */}
      <div className="research-section">
        <h3>{en ? "Hypothesis" : "假設"}</h3>
        <ul>
          <li>
            {en
              ? "(A) Security necessity — H₀: mean security_score ≤ 5.0 (physical-PBX baseline); H₁: > 5.0."
              : "(A) 資安必要性—H₀：平均 security_score ≤ 5.0（實體 PBX 基準）；H₁：> 5.0。"}
          </li>
          <li>
            {en
              ? "(B) Integration feasibility — H₀: mean complexity ≥ 5 (Medium-High+); H₁: < 5."
              : "(B) 整合可行性—H₀：平均複雜度 ≥ 5（偏高）；H₁：< 5。"}
          </li>
          <li>
            {en
              ? `Joint H₀ rejected only if BOTH legs reject, at α = ${data.alpha}.`
              : `兩面向皆拒絕方拒絕聯合 H₀，α = ${data.alpha}。`}
          </li>
        </ul>
      </div>

      {/* Results */}
      <div className="research-section">
        <h3>{en ? "Test results" : "檢定結果"}</h3>
        <table className="comparison-table">
          <thead>
            <tr>
              <th>{en ? "Leg" : "面向"}</th>
              <th>n</th>
              <th>{en ? "Mean" : "平均"}</th>
              <th>H₁</th>
              <th>{en ? "95% CI" : "95% 信賴區間"}</th>
              <th>p</th>
              <th>{en ? "Cohen's d" : "Cohen's d"}</th>
              <th>{en ? "Verdict" : "判定"}</th>
            </tr>
          </thead>
          <tbody>
            <LegRow label={en ? "Security" : "資安"} leg={data.security} />
            <LegRow label={en ? "Integration" : "整合"} leg={data.integration} />
          </tbody>
        </table>
        <p className="subtitle" style={{ marginTop: "1rem" }}>
          <span className={`maturity-badge ${data.joint_reject_h0 ? "mainstream" : "frontier"}`}>
            {pick("verdict")}
          </span>
        </p>
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
