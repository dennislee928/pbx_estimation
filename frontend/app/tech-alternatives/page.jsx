"use client";

import { useState } from "react";
import { t, getLang } from "../../i18n";
import alternatives from "../../data/awesome_list.json";

const L = getLang();

const splitList = (value) => String(value || "").split("; ").filter(Boolean);
const ALTS = alternatives.map((alt) => ({
  ...alt,
  cat: alt.category,
  pros: splitList(alt.pros),
  cons: splitList(alt.cons),
}));

const CAT_FILTERS = [
  { id: "all", labelEn: "All", labelZh: "全部" },
  { id: "web", labelEn: "Web / API (cable)", labelZh: "網路 / API（有線）" },
  { id: "non_web", labelEn: "Non-Web (wireless/radio)", labelZh: "非網路（無線/無線電）" },
];

export default function TechAlternativesPage() {
  const [filter, setFilter] = useState("all");
  const [expanded, setExpanded] = useState(null);
  const filtered = filter === "all" ? ALTS : ALTS.filter((a) => a.cat === filter);

  return (
    <div className="research-page">
      <h2>{t("techAlternatives")}</h2>
      <p className="subtitle">
        {L === "en"
          ? `Comprehensive catalog of alternatives to physical phone line command/trigger on edge devices. Covers ${ALTS.length} technologies across IP/API, brokered messaging, industrial, wired, wireless, cellular, satellite, serial, and electrical-contact media.`
          : `實體電話線觸發/控制邊緣裝置的替代方案完整目錄。涵蓋 ${ALTS.length} 種技術，橫跨 IP/API、訊息佇列、工業、有線、無線、蜂巢、衛星、序列匯流排與電氣接點媒介。`}
      </p>

      <div className="research-section">
        <h3>{L === "en" ? "Filter by Category" : "按類別篩選"}</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
          {CAT_FILTERS.map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              style={{
                padding: "6px 16px",
                borderRadius: 16,
                border: filter === f.id ? "2px solid #3b82f6" : "1px solid #d0d8e8",
                background: filter === f.id ? "#dbeafe" : "#fff",
                cursor: "pointer",
                fontSize: "0.8rem",
                fontWeight: filter === f.id ? 600 : 400,
              }}
            >
              {L === "en" ? f.labelEn : f.labelZh}
            </button>
          ))}
        </div>
      </div>

      <div className="research-section">
        {filtered.map((alt) => (
          <div
            key={alt.name}
            style={{
              background: "#fff",
              border: "1px solid #e0e0e0",
              borderRadius: 8,
              padding: 16,
              marginBottom: 12,
              cursor: "pointer",
            }}
            onClick={() => setExpanded(expanded === alt.name ? null : alt.name)}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <strong style={{ fontSize: "0.95rem" }}>{alt.name}</strong>
                <span style={{ marginLeft: 8, fontSize: "0.75rem", color: "#888" }}>{alt.cat === "web" ? "🌐" : "📡"} {alt.medium}</span>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                <span style={{ fontSize: "0.7rem", color: "#666", background: "#f0f2f5", padding: "2px 8px", borderRadius: 10 }}>{alt.latency}</span>
                <span style={{ fontSize: "0.7rem", color: "#666", background: "#f0f2f5", padding: "2px 8px", borderRadius: 10 }}>{alt.complexity}</span>
              </div>
            </div>
            {expanded === alt.name && (
              <div style={{ marginTop: 12, borderTop: "1px solid #eee", paddingTop: 12 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: "0.8rem", marginBottom: 8 }}>
                  <div><strong>{L === "en" ? "Reliability:" : "可靠性:"}</strong> {alt.reliability}</div>
                  <div><strong>{L === "en" ? "Security:" : "安全性:"}</strong> {alt.security}</div>
                </div>
                <div style={{ marginBottom: 8, fontSize: "0.8rem" }}>
                  <strong style={{ color: "#065f46" }}>{L === "en" ? "✓ Pros:" : "✓ 優點:"}</strong>
                  <ul style={{ marginTop: 4, paddingLeft: 16 }}>
                    {alt.pros.map((p) => <li key={p} style={{ fontSize: "0.8rem", lineHeight: 1.6 }}>{p}</li>)}
                  </ul>
                </div>
                <div style={{ fontSize: "0.8rem" }}>
                  <strong style={{ color: "#991b1b" }}>{L === "en" ? "✗ Cons:" : "✗ 缺點:"}</strong>
                  <ul style={{ marginTop: 4, paddingLeft: 16 }}>
                    {alt.cons.map((c) => <li key={c} style={{ fontSize: "0.8rem", lineHeight: 1.6 }}>{c}</li>)}
                  </ul>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
