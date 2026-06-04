"use client";

import { useState } from "react";
import { t, getLang } from "../../i18n";
import alternatives from "../../data/awesome_list.json";
import registry from "../../data/solution_registry.json";

const L = getLang();

const splitList = (value) => String(value || "").split("; ").filter(Boolean);
const searchable = (value) => String(value || "").toLowerCase();
const tokenize = (value) => searchable(value)
  .replace(/[^\p{L}\p{N}]+/gu, " ")
  .split(/\s+/)
  .filter((token) => token.length >= 2);

const SCENE_HINTS = [
  { keys: ["door", "lock", "access", "門", "門禁", "開門"], terms: ["door", "lock", "access", "relay", "dry contact", "osdp", "wiegand", "building", "門禁", "relay"] },
  { keys: ["alarm", "siren", "security", "警報", "保全", "告警"], terms: ["alarm", "siren", "security", "contact id", "sia", "cap", "警報", "security"] },
  { keys: ["factory", "plc", "scada", "industrial", "工廠", "產線", "plc"], terms: ["plc", "scada", "modbus", "opc", "profinet", "ethercat", "industrial", "工業"] },
  { keys: ["remote", "rural", "farm", "cellular", "遠端", "農場", "偏遠"], terms: ["lorawan", "cellular", "nb-iot", "lte-m", "satellite", "esim", "remote", "agriculture"] },
  { keys: ["audit", "queue", "retry", "稽核", "重送", "佇列"], terms: ["amqp", "rabbitmq", "kafka", "redis", "nats", "webhook", "audit", "retry", "queue"] },
  { keys: ["teams", "ucaas", "cloud", "call", "客服", "雲端", "電話"], terms: ["cloud", "ucaas", "cpaas", "api", "voice", "sip", "contact center", "teams"] },
];

const scoreText = (query, row, fields) => {
  const tokens = tokenize(query);
  if (!tokens.length) return 0;
  const text = searchable(fields.map((field) => row[field]).join(" "));
  let score = tokens.reduce((sum, token) => sum + (text.includes(token) ? 8 : 0), 0);
  for (const hint of SCENE_HINTS) {
    if (hint.keys.some((key) => searchable(query).includes(key))) {
      score += hint.terms.reduce((sum, term) => sum + (text.includes(term) ? 5 : 0), 0);
    }
  }
  if (/low|cheap|cost|便宜|低成本/.test(searchable(query)) && /low|very low|低/.test(text)) score += 10;
  if (/secure|security|tls|encrypt|安全|加密/.test(searchable(query)) && /tls|aes|mtls|oauth|secure|安全|加密/.test(text)) score += 10;
  if (/fast|latency|real.?time|即時|低延遲/.test(searchable(query)) && /<\s?(1|5|10|50|100)ms|real-time|low latency/i.test(text)) score += 10;
  return score;
};
const zhMedium = (medium) => ({
  ethernet_ip: "乙太網路/IP",
  ethernet_wire: "乙太網路線路",
  radio_ism: "ISM 無線電",
  cellular: "蜂巢網路",
  cellular_ip: "蜂巢/IP",
  cellular_lpwans: "蜂巢 LPWAN",
  cellular_esim: "eSIM/蜂巢",
  private_cellular: "私有 LTE/5G",
  satellite: "衛星",
  serial_wire: "序列線路",
  serial_ethernet: "序列/乙太網路",
  electrical_contact: "電氣接點",
  powerline: "電力線",
  fieldbus: "工業現場匯流排",
  building_bus: "建築控制匯流排",
  access_control: "門禁控制",
  edge_compute: "邊緣運算",
  edge_ai: "邊緣 AI",
})[medium] || String(medium || "").replaceAll("_", " ");

const zhScale = (value) => String(value || "")
  .replaceAll("remote devices", "遠端裝置")
  .replaceAll("industrial points", "工業點位")
  .replaceAll("local I/O points", "本地 I/O 點位")
  .replaceAll("building devices", "建築設備")
  .replaceAll("endpoints/events", "端點/事件")
  .replaceAll("devices", "裝置");

const zhCost = (value) => String(value || "")
  .replaceAll("Very Low", "極低")
  .replaceAll("Low-Medium", "低至中")
  .replaceAll("Medium-High", "中至高")
  .replaceAll("Low", "低")
  .replaceAll("Medium", "中")
  .replaceAll("High", "高")
  .replaceAll("subscription or message/device fees", "訂閱或按訊息/裝置計費")
  .replaceAll("platform/broker plus usage", "平台/訊息代理加用量計費")
  .replaceAll("high engineering/infrastructure", "高工程與基礎設施成本")
  .replaceAll("hardware plus installation", "硬體加安裝成本");

const zhIndustries = (value) => String(value || "")
  .replaceAll("Utilities", "公用事業")
  .replaceAll("Energy", "能源")
  .replaceAll("Water", "水務")
  .replaceAll("Industrial automation", "工業自動化")
  .replaceAll("Smart building", "智慧建築")
  .replaceAll("Facilities", "設施管理")
  .replaceAll("Hospitality", "旅宿")
  .replaceAll("Retail", "零售")
  .replaceAll("Logistics", "物流")
  .replaceAll("Agriculture", "農業")
  .replaceAll("Remote infrastructure", "遠端基礎設施")
  .replaceAll("Public safety", "公共安全")
  .replaceAll("SaaS", "SaaS")
  .replaceAll("Contact center", "客服中心")
  .replaceAll("Professional services", "專業服務")
  .replaceAll("Systems integration", "系統整合")
  .replaceAll("Enterprise", "企業")
  .replaceAll("SMB", "中小企業")
  .replaceAll("IoT", "物聯網");

const zhSummary = (alt) => {
  const category = alt.cat === "web" ? "網路/API" : "非 PSTN 實體線路";
  const protocols = splitList(alt.protocols).slice(0, 3).join("、") || zhMedium(alt.medium);
  return `${alt.name} 是 ${category} 替代方案，使用 ${protocols} 透過 ${zhMedium(alt.medium)} 承接 PBX/UCaaS 事件並執行「${alt.use_case}」。建議規模為 ${zhScale(alt.recommended_devices)}，常見於 ${zhIndustries(alt.industry_fit)}；延遲 ${alt.latency}、成本 ${zhCost(alt.cost_model)}，適合需要明確稽核、低延遲或脫離傳統電話線觸發的場景。`;
};

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
  const [scene, setScene] = useState("");
  const [expanded, setExpanded] = useState(null);
  const rankedAlternatives = ALTS
    .map((alt) => ({ ...alt, matchScore: scoreText(scene, alt, ["name", "description", "protocols", "medium", "latency", "reliability", "security", "complexity", "cost_model", "recommended_devices", "industry_fit", "use_case", "pros", "cons", "standards"]) }))
    .filter((a) => filter === "all" || a.cat === filter)
    .filter((a) => !scene.trim() || a.matchScore > 0)
    .sort((a, b) => (scene.trim() ? b.matchScore - a.matchScore : 0) || a.name.localeCompare(b.name));
  const filtered = rankedAlternatives;
  const rankedSolutions = registry
    .map((row) => ({ ...row, matchScore: scoreText(scene, row, ["name", "vendor", "continent", "country_code", "lifecycle_assigned", "tags", "description", "pros", "cons", "typical_customers", "recommended_terminals", "cost_band", "industry_fit"]) }))
    .filter((row) => scene.trim() && row.matchScore > 0)
    .sort((a, b) => b.matchScore - a.matchScore)
    .slice(0, 6);
  const ragContext = rankedAlternatives.slice(0, 3);

  return (
    <div className="research-page">
      <h2>{t("techAlternatives")}</h2>
      <p className="subtitle">
        {L === "en"
          ? `Comprehensive catalog of alternatives to physical phone line command/trigger on edge devices. Covers ${ALTS.length} technologies across IP/API, brokered messaging, industrial, wired, wireless, cellular, satellite, serial, and electrical-contact media.`
          : `實體電話線觸發/控制邊緣裝置的替代方案完整目錄。涵蓋 ${ALTS.length} 種技術，橫跨 IP/API、訊息佇列、工業、有線、無線、蜂巢、衛星、序列匯流排與電氣接點媒介。`}
      </p>

      <div className="research-section">
        <h3>{L === "en" ? "Scene Filter and RAG Ranking" : "場景篩選與 RAG 排序"}</h3>
        <div className="scene-filter">
          <label htmlFor="scene-filter">
            {L === "en" ? "Type your scene" : "輸入你的場景"}
          </label>
          <input
            id="scene-filter"
            value={scene}
            onChange={(event) => setScene(event.target.value)}
            placeholder={L === "en" ? "Example: hotel door relay, remote farm alarm, factory PLC audit trail" : "例如：飯店房門繼電器、偏遠農場警報、工廠 PLC 稽核"}
          />
          <small>
            {L === "en"
              ? "Local RAG-style retrieval ranks alternatives and PBX/UCaaS solutions by scene terms, protocols, industries, security, latency, and cost signals."
              : "本機 RAG 式檢索會依場景詞、協定、產業、安全、延遲與成本訊號，排序替代技術與 PBX/UCaaS 解決方案。"}
          </small>
        </div>
        {scene.trim() && (
          <div className="rag-panel">
            <strong>{L === "en" ? "RAG recommendation" : "RAG 建議"}</strong>
            <p>
              {ragContext.length
                ? (L === "en"
                  ? `Prioritize ${ragContext.map((a) => a.name).join(", ")} because they match the entered scene across control path, deployment medium, cost/security posture, or industry fit.`
                  : `優先評估 ${ragContext.map((a) => a.name).join("、")}，因為它們在控制路徑、部署媒介、成本/安全性或產業適配上最符合輸入場景。`)
                : (L === "en" ? "No strong match yet. Try adding device type, site type, latency, network, or cost constraints." : "目前沒有明確匹配。可加入裝置類型、場域、延遲、網路或成本限制。")}
            </p>
          </div>
        )}
      </div>

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

      {scene.trim() && (
        <div className="research-section">
          <h3>{L === "en" ? "Prioritized PBX/UCaaS Solutions" : "優先解決方案"}</h3>
          <div className="ranked-solution-grid">
            {rankedSolutions.map((row) => (
              <a href={row.resource_url || "#"} target="_blank" rel="noreferrer" className="ranked-solution" key={`${row.vendor}-${row.name}`}>
                <strong>{row.name}</strong>
                <span>{row.vendor} · {String(row.country_code).toUpperCase()} · {row.lifecycle_assigned}</span>
                <small>{row.recommended_terminals} · {row.cost_band}</small>
              </a>
            ))}
          </div>
        </div>
      )}

      <div className="research-section">
        <h3>{L === "en" ? `Prioritized Alternatives (${filtered.length})` : `優先替代技術（${filtered.length}）`}</h3>
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
                <span style={{ marginLeft: 8, fontSize: "0.75rem", color: "#888" }}>{alt.cat === "web" ? "IP" : "RF"} {L === "en" ? alt.medium : zhMedium(alt.medium)}</span>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                {scene.trim() && <span style={{ fontSize: "0.7rem", color: "#155e75", background: "#cffafe", padding: "2px 8px", borderRadius: 10 }}>RAG {alt.matchScore}</span>}
                <span style={{ fontSize: "0.7rem", color: "#666", background: "#f0f2f5", padding: "2px 8px", borderRadius: 10 }}>{alt.latency}</span>
                <span style={{ fontSize: "0.7rem", color: "#666", background: "#f0f2f5", padding: "2px 8px", borderRadius: 10 }}>{alt.complexity}</span>
              </div>
            </div>
            {expanded === alt.name && (
              <div style={{ marginTop: 12, borderTop: "1px solid #eee", paddingTop: 12 }}>
                <p style={{ fontSize: "0.82rem", lineHeight: 1.6, marginTop: 0 }}>
                  {L === "en" ? `${alt.description} Use case: ${alt.use_case}. Recommended scale: ${alt.recommended_devices}; industry fit: ${alt.industry_fit}.` : zhSummary(alt)}
                </p>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: "0.8rem", marginBottom: 8 }}>
                  <div><strong>{L === "en" ? "Reliability:" : "可靠性:"}</strong> {alt.reliability}</div>
                  <div><strong>{L === "en" ? "Security:" : "安全性:"}</strong> {alt.security}</div>
                  <div><strong>{L === "en" ? "Recommended terminals/devices:" : "建議終端/裝置數:"}</strong> {L === "en" ? alt.recommended_devices : zhScale(alt.recommended_devices)}</div>
                  <div><strong>{L === "en" ? "Cost model:" : "成本/計費模式:"}</strong> {L === "en" ? alt.cost_model : zhCost(alt.cost_model)}</div>
                  <div style={{ gridColumn: "1 / -1" }}><strong>{L === "en" ? "Industries:" : "適用產業:"}</strong> {L === "en" ? alt.industry_fit : zhIndustries(alt.industry_fit)}</div>
                  <div style={{ gridColumn: "1 / -1" }}>
                    <strong>{L === "en" ? "Source:" : "來源:"}</strong>{" "}
                    {alt.resource_url ? <a href={alt.resource_url} target="_blank" rel="noreferrer">{alt.resource_url}</a> : "-"}
                  </div>
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
