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

      {/* Why the kept PBX is the risk */}
      <div className="research-section">
        <h3>{en ? "Why the kept PBX is the risk" : "為何「保留 PBX」才是風險"}</h3>
        <ul>
          {data.baseline_risks.map((r) => (
            <li key={r.source_url}>
              {en ? r.text_en : r.text_zh}{" "}
              <a href={r.source_url} target="_blank" rel="noreferrer">
                [{r.source_name}]
              </a>
            </li>
          ))}
        </ul>
      </div>

      {/* Integration difficulty (heterogeneous vendors) */}
      <div className="research-section">
        <h3>{en ? "Integration difficulty (heterogeneous vendors)" : "整合難度（異質廠商）"}</h3>
        <p className="subtitle">
          {en
            ? `The target IP protocols are individually low-friction (mean friction index ${data.ip_friction_mean}/10); the real cost is a bounded one-time bridge to legacy vendors.`
            : `目標 IP 協定本身整合摩擦低（平均摩擦指數 ${data.ip_friction_mean}/10）；真正成本在於對舊廠商的一次性橋接。`}
        </p>
        <ul>
          {data.integration_friction.map((r) => (
            <li key={r.source_url}>
              {en ? r.text_en : r.text_zh}{" "}
              <a href={r.source_url} target="_blank" rel="noreferrer">
                [{r.source_name}]
              </a>
            </li>
          ))}
        </ul>
      </div>

      {/* Hypothesis */}
      <div className="research-section">
        <h3>{en ? "Hypothesis" : "假設"}</h3>
        <ul>
          <li>{en ? data.hypothesis_a_en : data.hypothesis_a_zh}</li>
          <li>{en ? data.hypothesis_b_en : data.hypothesis_b_zh}</li>
          <li>
            {en
              ? `Joint H₀ rejected only if BOTH legs reject, at α = ${data.alpha}.`
              : `兩面向皆拒絕方拒絕聯合 H₀，α = ${data.alpha}。`}
          </li>
        </ul>
        <p className="subtitle">{en ? data.population_note_en : data.population_note_zh}</p>
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
