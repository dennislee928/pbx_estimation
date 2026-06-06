"use client";

import { useState } from "react";
import { t, getLang } from "../../i18n";
import alternatives from "../../data/awesome_list.json";
import registry from "../../data/solution_registry.json";
import crawlerSeed from "../../data/crawler_seed_context.json";

const L = getLang();
const CLOUD_RAG_ENDPOINT = process.env.NEXT_PUBLIC_CLOUD_RAG_ENDPOINT || "";

const splitList = (value) => String(value || "").split("; ").filter(Boolean);
const searchable = (value) => String(value || "").toLowerCase();
const tokenize = (value) => searchable(value)
  .replace(/[^\p{L}\p{N}]+/gu, " ")
  .split(/\s+/)
  .filter((token) => token.length >= 2);

const textMatches = (query, row, fields) => {
  const tokens = tokenize(query);
  if (!tokens.length) return true;
  const text = searchable(fields.map((field) => row[field]).join(" "));
  return tokens.some((token) => text.includes(token));
};

// --- Negative transport constraints (mirrors rag_engine/src/worker.js) ---
// Lets the in-browser list respect phrases like "不可以用乙太網路" so the client
// catalog matches what the cloud RAG returns.
const TRANSPORT_EXCLUSIONS = [
  { keys: ["乙太網路線", "網路線", "ethernet cable", "ethernet wire", "rj45", "rj-45"], tokens: ["ethernet_wire", "ethernet", "rj45", "lan"] },
  { keys: ["乙太網路", "ethernet", "ip網路", "ip network", "區域網路"], tokens: ["ethernet", "ethernet_ip", "ethernet_wire", "serial_ethernet", "lan"] },
  { keys: ["類比電話線", "傳統電話線", "傳統電話", "類比電話", "類比線路", "類比", "電話線", "市話", "analog phone", "analog line", "analog", "analogue", "pstn line", "pots", "landline"], tokens: ["analog", "pstn", "pots", "fxs", "fxo", "tdm", "copper", "phone_line"] },
  { keys: ["pstn", "傳統電話網路"], tokens: ["pstn", "pots", "tdm", "analog"] },
  { keys: ["wifi", "wi-fi", "無線網路", "wlan"], tokens: ["wifi", "wifi_direct", "wlan", "802.11"] },
  { keys: ["蜂巢", "行動網路", "cellular", "lte", "5g", "nb-iot"], tokens: ["cellular", "cellular_ip", "cellular_lpwans", "cellular_esim", "private_cellular", "lte", "5g", "nb-iot"] },
  { keys: ["衛星", "satellite"], tokens: ["satellite", "satellite_navigation"] },
  { keys: ["序列", "serial", "rs-232", "rs-485"], tokens: ["serial_wire", "serial_ethernet", "modbus"] },
  { keys: ["藍牙", "bluetooth", "ble"], tokens: ["bluetooth", "ble", "radio_802_15_4"] },
  { keys: ["紅外線", "infrared"], tokens: ["infrared", "optical_signal"] },
];
const NEGATION_MARKERS = [
  "不可以用", "不可以", "不能用", "不能", "不可", "不使用", "不要用", "不要", "不得", "禁用", "禁止", "避免", "排除", "無法使用", "沒有",
  "cannot use", "can not use", "can't use", "cannot", "can't", "without", "no ", "not ", "avoid", "exclude", "excluding", "must not",
];

const parseExclusionTokens = (scene) => {
  const text = searchable(scene);
  const tokens = new Set();
  for (const group of TRANSPORT_EXCLUSIONS) {
    for (const key of group.keys) {
      const needle = searchable(key);
      let from = 0;
      let idx = text.indexOf(needle, from);
      while (idx !== -1) {
        const before = text.slice(Math.max(0, idx - 12), idx);
        if (NEGATION_MARKERS.some((marker) => before.includes(searchable(marker)))) {
          group.tokens.forEach((token) => tokens.add(token));
          break;
        }
        from = idx + needle.length;
        idx = text.indexOf(needle, from);
      }
    }
  }
  return [...tokens];
};

const rowExcluded = (row, tokens) => {
  if (!tokens.length) return false;
  const text = searchable([row.medium, row.protocols, row.standards, row.category, row.tags, row.description].join(" "));
  return tokens.some((token) => text.includes(searchable(token)));
};

const normalizeCloudItems = (items) => (Array.isArray(items) ? items : [])
  .map((item, index) => {
    if (typeof item === "string") return { name: item, rank: index + 1, reason: "" };
    return {
      type: item.type || "",
      name: item.name || item.id || "",
      rank: Number(item.rank || index + 1),
      label: item.label || item.transport_label || "",
      transport_label: item.transport_label || item.label || "",
      transport_type: item.transport_type || "",
      suitability_percent: item.suitability_percent || "",
      cost: item.cost || "",
      risk_level: item.risk_level || "",
      pros: Array.isArray(item.pros) ? item.pros : splitList(item.pros),
      cons: Array.isArray(item.cons) ? item.cons : splitList(item.cons),
      reason: item.reason || item.rationale || item.summary || "",
      excerpt: item.excerpt || "",
      key: item.key || "",
      score: item.score || "",
      resource_url: item.resource_url || "",
    };
  })
  .filter((item) => item.name);
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
  sensor_bus: "感測器匯流排",
  board_bus: "板級匯流排",
  usb: "USB",
  av_bus: "影音控制匯流排",
  infrared: "紅外線",
  near_field: "近場感應",
  optical_signal: "光學訊號",
  acoustic_signal: "聲學訊號",
  visual_signal: "視覺訊號",
  sensor_trigger: "感測觸發",
  mechanical_actuation: "機械致動",
  pneumatic: "氣壓",
  hydraulic: "液壓",
  magnetic: "磁性/霍爾",
  barcode_qr: "條碼/QR",
  paper_document: "紙本/文件",
  manual_process: "人工流程",
  physical_key: "實體鑰匙/鎖具",
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
  .replaceAll("hardware plus installation", "硬體加安裝成本")
  .replaceAll("hardware, fixture, or process-change cost", "硬體、治具或流程變更成本");

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
  .replaceAll("Healthcare", "醫療")
  .replaceAll("Field service", "現場服務")
  .replaceAll("Maintenance", "維護")
  .replaceAll("Manufacturing", "製造")
  .replaceAll("Safety systems", "安全系統")
  .replaceAll("Venues", "場館")
  .replaceAll("Broadcast", "廣播/製播")
  .replaceAll("Digital signage", "數位看板")
  .replaceAll("Security", "保全")
  .replaceAll("Access control", "門禁")
  .replaceAll("Compliance", "合規")
  .replaceAll("Heavy equipment", "重型設備")
  .replaceAll("Senior care", "長照")
  .replaceAll("Back office", "後勤辦公")
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
  { id: "non_web", labelEn: "Non-network / physical", labelZh: "非網路 / 實體媒介" },
];

const transportLabel = (row) => {
  if (row?.transport_label || row?.label) return row.transport_label || row.label;
  if (row?.transport_type === "non_network_physical" || row?.cat === "non_web" || row?.category === "non_web") {
    return L === "en" ? "Non-network / physical" : "非網路 / 實體媒介";
  }
  return L === "en" ? "Web / API (cable)" : "網路 / API（有線）";
};

const transportClass = (row) => {
  const label = transportLabel(row);
  return row?.transport_type === "non_network_physical" || /非網路|non-network|physical/i.test(label)
    ? "non-network"
    : "network";
};

const cloudCategory = (row) => {
  if (row.transport_type === "non_network_physical" || transportClass(row) === "non-network") return "non_web";
  if (row.transport_type === "network_api_wired") return "web";
  const alt = ALTS.find((item) => item.name === row.name);
  return alt?.cat || "web";
};

const rowsForCloudTable = (cloudRag) => {
  const explicit = cloudRag?.tables?.rag_response || cloudRag?.rag_response_table;
  if (Array.isArray(explicit) && explicit.length) return normalizeCloudItems(explicit);
  return [
    ...normalizeCloudItems(cloudRag?.alternatives).map((row) => ({ ...row, type: row.type || "alternative" })),
    ...normalizeCloudItems(cloudRag?.solutions).map((row) => ({ ...row, type: row.type || "solution" })),
  ];
};

// --- Solution-catalog dropdown filters (vendor / region / category / scale /
// cost / industry / source). Multi-value fields are split into discrete tokens.
const domainOf = (url) => {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
};

const SOL_FILTER_DEFS = [
  { key: "vendor", labelEn: "Vendor", labelZh: "供應商", get: (r) => [r.vendor].filter(Boolean) },
  { key: "continent", labelEn: "Region", labelZh: "區域", get: (r) => [r.continent].filter(Boolean) },
  { key: "tags", labelEn: "Category", labelZh: "類別", get: (r) => splitTokens(r.tags, ",") },
  { key: "recommended_terminals", labelEn: "Recommended terminals", labelZh: "建議終端數", get: (r) => [r.recommended_terminals].filter(Boolean) },
  { key: "cost_band", labelEn: "Cost", labelZh: "成本", get: (r) => [r.cost_band].filter(Boolean) },
  { key: "industry_fit", labelEn: "Industry", labelZh: "適用產業", get: (r) => splitTokens(r.industry_fit, ";") },
  { key: "source", labelEn: "Source", labelZh: "來源", get: (r) => [domainOf(r.resource_url)].filter(Boolean) },
];

const splitTokensImpl = (value, sep) => String(value || "")
  .split(sep)
  .map((token) => token.trim())
  .filter(Boolean);
function splitTokens(value, sep) { return splitTokensImpl(value, sep); }

const SOL_FILTER_OPTIONS = Object.fromEntries(
  SOL_FILTER_DEFS.map((def) => [
    def.key,
    [...new Set(registry.flatMap((row) => def.get(row)))].sort((a, b) => String(a).localeCompare(String(b))),
  ]),
);

const matchesSolutionFilters = (row, filters) => SOL_FILTER_DEFS.every((def) => {
  const selected = filters[def.key];
  if (!selected || selected === "all") return true;
  return def.get(row).includes(selected);
});

const emptySolutionFilters = Object.fromEntries(SOL_FILTER_DEFS.map((def) => [def.key, "all"]));

const mediumBadge = (alt) => {
  if (alt.cat === "web") return "IP";
  const medium = searchable(alt.medium);
  if (/radio|wifi|cellular|satellite|dect|uwb|lpwan|near_field|rfid|nfc/.test(medium)) return "RF";
  if (/serial|fieldbus|building_bus|board_bus|usb|av_bus|electrical|powerline|access_control/.test(medium)) return "WIRE";
  if (/optical|visual|infrared/.test(medium)) return "OPT";
  if (/acoustic|audio/.test(medium)) return "AUDIO";
  if (/mechanical|pneumatic|hydraulic|magnetic|physical|manual|paper|barcode|qr|sensor/.test(medium)) return "PHYS";
  return "ALT";
};

export default function TechAlternativesPage() {
  const [filter, setFilter] = useState("all");
  const [scene, setScene] = useState("");
  const [solFilters, setSolFilters] = useState(emptySolutionFilters);
  const [expanded, setExpanded] = useState(null);
  const [cloudRag, setCloudRag] = useState(null);
  const [cloudRagStatus, setCloudRagStatus] = useState("idle");
  const [cloudRagError, setCloudRagError] = useState("");

  const cloudAlternativeRanks = new Map(normalizeCloudItems(cloudRag?.alternatives).map((item) => [item.name, item]));
  const cloudSolutionRanks = new Map(normalizeCloudItems(cloudRag?.solutions).map((item) => [item.name, item]));
  const cloudDocuments = normalizeCloudItems(cloudRag?.documents);
  const cloudTableRows = rowsForCloudTable(cloudRag);
  const visibleCloudTableRows = cloudTableRows.filter((row) => filter === "all" || cloudCategory(row) === filter);
  const exclusionTokens = parseExclusionTokens(scene);
  const filtered = ALTS
    .filter((a) => filter === "all" || a.cat === filter)
    .filter((a) => !rowExcluded(a, exclusionTokens))
    .filter((a) => textMatches(scene, a, ["name", "description", "protocols", "medium", "latency", "reliability", "security", "complexity", "cost_model", "recommended_devices", "industry_fit", "use_case", "pros", "cons", "standards"]))
    .sort((a, b) => {
      const aRank = cloudAlternativeRanks.get(a.name)?.rank || Number.MAX_SAFE_INTEGER;
      const bRank = cloudAlternativeRanks.get(b.name)?.rank || Number.MAX_SAFE_INTEGER;
      return aRank - bRank || a.name.localeCompare(b.name);
    });
  const solFiltersActive = SOL_FILTER_DEFS.some((def) => solFilters[def.key] && solFilters[def.key] !== "all");
  const rankedSolutions = registry
    .filter((row) => !rowExcluded(row, exclusionTokens))
    .filter((row) => matchesSolutionFilters(row, solFilters))
    .filter((row) => !scene.trim() || textMatches(scene, row, ["name", "vendor", "continent", "country_code", "lifecycle_assigned", "tags", "description", "pros", "cons", "typical_customers", "recommended_terminals", "cost_band", "industry_fit"]) || cloudSolutionRanks.has(row.name))
    .sort((a, b) => {
      const aRank = cloudSolutionRanks.get(a.name)?.rank || Number.MAX_SAFE_INTEGER;
      const bRank = cloudSolutionRanks.get(b.name)?.rank || Number.MAX_SAFE_INTEGER;
      return aRank - bRank || a.name.localeCompare(b.name);
    })
    .slice(0, solFiltersActive ? 60 : 12);
  const cloudRecommendation = cloudRag?.recommendation || cloudRag?.summary || "";

  async function askCloudRag() {
    if (!scene.trim() || !CLOUD_RAG_ENDPOINT) return;
    setCloudRagStatus("loading");
    setCloudRagError("");
    try {
      const response = await fetch(CLOUD_RAG_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scene,
          language: L,
          crawler_seed_context: crawlerSeed,
          alternatives: ALTS.map(({ name, category, medium, description, protocols, latency, reliability, security, complexity, cost_model, recommended_devices, industry_fit, use_case, pros, cons, resource_url }) => ({
            name,
            category,
            medium,
            description,
            protocols,
            latency,
            reliability,
            security,
            complexity,
            cost_model,
            recommended_devices,
            industry_fit,
            use_case,
            pros,
            cons,
            resource_url,
          })),
          solutions: registry.map(({ name, vendor, continent, country_code, lifecycle_assigned, tags, description, pros, cons, typical_customers, recommended_terminals, cost_band, industry_fit, resource_url }) => ({
            name,
            vendor,
            continent,
            country_code,
            lifecycle_assigned,
            tags,
            description,
            pros,
            cons,
            typical_customers,
            recommended_terminals,
            cost_band,
            industry_fit,
            resource_url,
          })),
          expected_response_schema: {
            recommendation: "short explanation",
            alternatives: [{ name: "existing alternative name", rank: 1, transport_label: "網路 / API（有線） or 非網路 / 實體媒介", reason: "why it fits" }],
            solutions: [{ name: "existing solution name", rank: 1, transport_label: "網路 / API（有線） or 非網路 / 實體媒介", reason: "why it fits" }],
            rag_response_table: [{ type: "solution or alternative", rank: 1, name: "existing row name", label: "網路 / API（有線） or 非網路 / 實體媒介", suitability_percent: 90, cost: "cost profile", risk_level: "Low/Medium/High", pros: [], cons: [], reason: "why it fits", resource_url: "source URL" }],
          },
        }),
      });
      if (!response.ok) throw new Error(`Cloud RAG returned HTTP ${response.status}`);
      setCloudRag(await response.json());
      setCloudRagStatus("done");
    } catch (error) {
      setCloudRagError(error instanceof Error ? error.message : String(error));
      setCloudRagStatus("error");
    }
  }

  return (
    <div className="research-page">
      <h2>{t("techAlternatives")}</h2>
      <p className="subtitle">
        {L === "en"
          ? `Comprehensive catalog of alternatives to physical phone line command/trigger on edge devices. Covers ${ALTS.length} technologies across IP/API, brokered messaging, industrial, wired, RF, cellular, satellite, serial, dry-contact, optical, acoustic, mechanical, pneumatic, hydraulic, QR/barcode, and human-workflow media.`
          : `實體電話線觸發/控制邊緣裝置的替代方案完整目錄。涵蓋 ${ALTS.length} 種技術，橫跨 IP/API、訊息佇列、工業、有線、RF、蜂巢、衛星、序列匯流排、乾接點、光學、聲學、機械、氣壓、液壓、QR/條碼與人工流程媒介。`}
      </p>

      <div className="research-section">
        <h3>{L === "en" ? "Scene Filter and Cloud RAG" : "場景篩選與雲端 RAG"}</h3>
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
              ? "Keyword filtering happens in the browser. Prioritization is requested from a cloud RAG endpoint configured by NEXT_PUBLIC_CLOUD_RAG_ENDPOINT."
              : "瀏覽器只做關鍵字篩選；優先排序會送到 NEXT_PUBLIC_CLOUD_RAG_ENDPOINT 設定的雲端 RAG 端點處理。"}
          </small>
          <button
            type="button"
            onClick={askCloudRag}
            disabled={!scene.trim() || !CLOUD_RAG_ENDPOINT || cloudRagStatus === "loading"}
            className="cloud-rag-button"
          >
            {cloudRagStatus === "loading"
              ? (L === "en" ? "Asking cloud RAG..." : "雲端 RAG 分析中...")
              : (L === "en" ? "Prioritize with Cloud RAG" : "使用雲端 RAG 優先排序")}
          </button>
          {!CLOUD_RAG_ENDPOINT && (
            <small className="cloud-rag-warning">
              {L === "en"
                ? "Set NEXT_PUBLIC_CLOUD_RAG_ENDPOINT at build time to enable cloud RAG."
                : "建置時設定 NEXT_PUBLIC_CLOUD_RAG_ENDPOINT 才會啟用雲端 RAG。"}
            </small>
          )}
        </div>
        {(cloudRecommendation || cloudRagStatus === "error") && (
          <div className="rag-panel">
            <strong>{L === "en" ? "Cloud RAG recommendation" : "雲端 RAG 建議"}</strong>
            <p>
              {cloudRagStatus === "error" ? cloudRagError : cloudRecommendation}
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

      <div className="research-section">
        <h3>
          {L === "en"
            ? `Solution Catalog with scale & sources (${rankedSolutions.length})`
            : `含規模建議與來源網址的方案目錄（${rankedSolutions.length}）`}
        </h3>
        <div className="solution-filter-bar" style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14, alignItems: "flex-end" }}>
          {SOL_FILTER_DEFS.map((def) => (
            <label key={def.key} style={{ display: "flex", flexDirection: "column", fontSize: "0.72rem", color: "#555", gap: 3 }}>
              {L === "en" ? def.labelEn : def.labelZh}
              <select
                value={solFilters[def.key]}
                onChange={(event) => setSolFilters({ ...solFilters, [def.key]: event.target.value })}
                style={{ padding: "5px 8px", borderRadius: 6, border: "1px solid #d0d8e8", fontSize: "0.78rem", maxWidth: 200 }}
              >
                <option value="all">{L === "en" ? "All" : "全部"}</option>
                {SOL_FILTER_OPTIONS[def.key].map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            </label>
          ))}
          {solFiltersActive && (
            <button
              type="button"
              onClick={() => setSolFilters(emptySolutionFilters)}
              style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #d0d8e8", background: "#fff", cursor: "pointer", fontSize: "0.75rem" }}
            >
              {L === "en" ? "Reset filters" : "清除篩選"}
            </button>
          )}
        </div>
        {rankedSolutions.length === 0 ? (
          <p style={{ fontSize: "0.82rem", color: "#888" }}>
            {L === "en" ? "No solutions match the current filters." : "沒有符合目前篩選條件的方案。"}
          </p>
        ) : (
          <div className="ranked-solution-grid">
            {rankedSolutions.map((row) => (
              <a href={row.resource_url || "#"} target="_blank" rel="noreferrer" className="ranked-solution" key={`${row.vendor}-${row.name}`}>
                <strong>{row.name}</strong>
                <span>{row.vendor} · {String(row.country_code).toUpperCase()} · {row.lifecycle_assigned}</span>
                <small>{row.recommended_terminals} · {row.cost_band}</small>
                <small style={{ color: "#2563eb" }}>{domainOf(row.resource_url) || "—"}</small>
              </a>
            ))}
          </div>
        )}
      </div>

      {cloudDocuments.length > 0 && (
        <div className="research-section">
          <h3>{L === "en" ? "Retrieved Report/Data Evidence" : "已檢索報告/資料證據"}</h3>
          <div className="ranked-solution-grid">
            {cloudDocuments.map((doc) => (
              <div className="ranked-solution" key={`${doc.rank}-${doc.name}`}>
                <strong>#{doc.rank} {doc.name}</strong>
                <span>{doc.reason}</span>
                {doc.excerpt && <small>{doc.excerpt}</small>}
              </div>
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
                <span style={{ marginLeft: 8, fontSize: "0.75rem", color: "#888" }}>{mediumBadge(alt)} {L === "en" ? alt.medium : zhMedium(alt.medium)}</span>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                {cloudAlternativeRanks.has(alt.name) && <span style={{ fontSize: "0.7rem", color: "#155e75", background: "#cffafe", padding: "2px 8px", borderRadius: 10 }}>Cloud RAG #{cloudAlternativeRanks.get(alt.name).rank}</span>}
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
