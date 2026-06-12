"use client";

import { getLang } from "../../i18n";
import data from "../../data/financial_hypothesis.json";

const L = getLang();
const en = L === "en";
const pick = (base) => data[`${base}_${en ? "en" : "zh"}`];

const HORIZONS = [3, 5, 10];
const SCOPES = [
  { key: "Taiwan", en: "Taiwan", zh: "台灣" },
  { key: "Worldwide", en: "Worldwide", zh: "全球" },
];

const fmtUsd = (v) => `${v < 0 ? "−" : ""}$${Math.abs(v).toLocaleString()}`;

export default function FinancialHypothesisPage() {
  const rowFor = (scope, h) =>
    data.rows.find((r) => r.scope === scope && r.horizon_years === h);
  const a = data.assumptions;

  return (
    <div className="research-page">
      <h2>{pick("title")}</h2>
      <p className="subtitle">{pick("method")}</p>

      {/* Assumptions */}
      <div className="research-section">
        <h3>{en ? "Model assumptions (real prices)" : "模型假設（真實價格）"}</h3>
        <ul>
          <li>
            {en ? "Discount rate: " : "折現率："}
            <strong>{(a.discount_rate * 100).toFixed(0)}%</strong>
          </li>
          <li>
            {en ? "Physical PBX upfront: " : "實體 PBX 前期資本支出："}
            <strong>${a.physical_capex_usd[0]}–${a.physical_capex_usd[1]} / seat</strong>
          </li>
          <li>
            {en ? "Physical annual maintenance: " : "實體年度維護："}
            <strong>
              {(a.physical_maint_frac[0] * 100).toFixed(0)}–
              {(a.physical_maint_frac[1] * 100).toFixed(0)}% {en ? "of capex" : "資本支出"}
            </strong>
          </li>
          <li>
            {en ? "Cloud / IP-PBX subscription: " : "雲端／IP-PBX 訂閱："}
            <strong>
              ${a.cloud_usd_per_seat_month[0]}–${a.cloud_usd_per_seat_month[1]} / seat / mo
            </strong>
          </li>
          <li>
            {en ? "Monte-Carlo draws per market: " : "每市場蒙地卡羅抽樣數："}
            <strong>{a.monte_carlo_draws.toLocaleString()}</strong>
          </li>
        </ul>
        <p>{en ? a.note_en : a.note_zh}</p>
      </div>

      {/* Results */}
      <div className="research-section">
        <h3>{en ? "Hypothesis test results" : "假設檢定結果"}</h3>
        <p>
          {en
            ? "H₀: replacing is NOT financially reasonable (mean NPV(keep − replace) ≤ 0). Δ > 0 ⇒ replacement saves money. Reject H₀ at p < 0.05."
            : "H₀：汰換不具財務合理性（NPV(續用 − 汰換) 平均值 ≤ 0）。Δ > 0 代表汰換可省錢。p < 0.05 時拒絕 H₀。"}
        </p>
        <table className="comparison-table">
          <thead>
            <tr>
              <th>{en ? "Scope" : "範圍"}</th>
              <th>{en ? "Horizon" : "期間"}</th>
              <th>{en ? "Mean Δ NPV/seat" : "平均 Δ NPV/席位"}</th>
              <th>{en ? "95% CI" : "95% 信賴區間"}</th>
              <th>p</th>
              <th>{en ? "Cohen's d" : "Cohen's d"}</th>
              <th>{en ? "Verdict" : "判定"}</th>
            </tr>
          </thead>
          <tbody>
            {SCOPES.flatMap((s) =>
              HORIZONS.map((h) => {
                const r = rowFor(s.key, h);
                if (!r) return null;
                return (
                  <tr key={`${s.key}-${h}`}>
                    <td>{en ? s.en : s.zh}</td>
                    <td>{h}{en ? "y" : " 年"}</td>
                    <td>{fmtUsd(r.mean_delta_usd)}</td>
                    <td>
                      {fmtUsd(r.ci_low_usd)} … {fmtUsd(r.ci_high_usd)}
                    </td>
                    <td>{r.p_value.toFixed(3)}</td>
                    <td>{r.cohens_d.toFixed(2)}</td>
                    <td>
                      <span
                        className={`maturity-badge ${r.reject_h0 ? "mainstream" : "frontier"}`}
                      >
                        {en ? r.verdict_en : r.verdict_zh}
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
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
