"use client";

import { t, getLang } from "../../i18n";
import registry from "../../data/solution_registry.json";

const L = getLang();

const CATEGORIES = [
  { id: "cutting_edge", labelEn: "Cutting Edge", labelZh: "前沿技術" },
  { id: "mature_active", labelEn: "Most Mature (Active)", labelZh: "成熟技術（活躍）" },
  { id: "most_used_current", labelEn: "Most Used (Current)", labelZh: "主流採用（現行）" },
  { id: "most_used_eol", labelEn: "Most Used (EOL)", labelZh: "主流採用（已停產）" },
];

const SAMPLE_ORDER = ["cutting_edge", "mature_active", "most_used_current", "most_used_eol"];
const SAMPLES = SAMPLE_ORDER.flatMap((cat) =>
  registry.filter((row) => row.lifecycle_assigned === cat).slice(0, 8)
);

const continentCount = new Set(registry.map((row) => row.continent)).size;
const countryCount = new Set(registry.map((row) => row.country_code)).size;
const vendorCount = new Set(registry.map((row) => row.vendor)).size;
const byContinent = registry.reduce((acc, row) => {
  acc[row.continent] = (acc[row.continent] || 0) + 1;
  return acc;
}, {});
const byCategory = registry.reduce((acc, row) => {
  acc[row.lifecycle_assigned] = (acc[row.lifecycle_assigned] || 0) + 1;
  return acc;
}, {});

export default function ProductResearchPage() {
  return (
    <div className="research-page">
      <h2>{t("productResearch")}</h2>
      <p className="subtitle">
        {L === "en"
          ? `Vendor landscape analysis, lifecycle classification, and market positioning for ${registry.length} PBX/VoIP/UCaaS solutions across ${continentCount} continent groups and ${countryCount} countries/regions from ${vendorCount} vendors.`
          : `針對全球 ${continentCount} 個洲別群組、${countryCount} 個國家/地區、${vendorCount} 家供應商的 ${registry.length} 個 PBX/VoIP/UCaaS 解決方案進行供應商格局分析、生命週期分類與市場定位。`}
      </p>

      <div className="research-section">
        <h3>{L === "en" ? "Lifecycle Classification Framework" : "生命週期分類框架"}</h3>
        <table className="registry-table">
          <thead>
            <tr>
              <th>{L === "en" ? "Category" : "類別"}</th>
              <th>{L === "en" ? "Definition" : "定義"}</th>
              <th>{L === "en" ? "Examples" : "範例"}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><span className="category-badge cutting_edge">{L === "en" ? "Cutting Edge" : "前沿技術"}</span></td>
              <td>{L === "en" ? "Latest-gen tech entering market (2023+). AI, API-first, WebRTC-native." : "最新世代技術（2023+）。AI、API-first、WebRTC 原生。"}</td>
              <td>Zoom Phone, Twilio Flex, Teams Phone, EVOX</td>
            </tr>
            <tr>
              <td><span className="category-badge mature_active">{L === "en" ? "Mature (Active)" : "成熟（活躍）"}</span></td>
              <td>{L === "en" ? "Stable, proven, still supported/sold. Well-established protocols." : "穩定、成熟、仍獲支援/販售。已建立完善協議。"}</td>
              <td>Asterisk/FreePBX, 3CX, Cisco CM, FreeSWITCH</td>
            </tr>
            <tr>
              <td><span className="category-badge most_used_current">{L === "en" ? "Most Used (Current)" : "主流採用（現行）"}</span></td>
              <td>{L === "en" ? "Highest market share, not yet EOL. Widely deployed in specific regions." : "最高市佔率，尚未 EOL。在特定區域廣泛部署。"}</td>
              <td>RingCentral, CHT 雲端總機, NTT Cloud, Auerswald</td>
            </tr>
            <tr>
              <td><span className="category-badge most_used_eol">{L === "en" ? "Most Used (EOL)" : "主流採用（已停產）"}</span></td>
              <td>{L === "en" ? "Legacy systems, EOL/EOS, still in production. Security risk." : "老舊系統，EOL/EOS，仍在運作。存在資安風險。"}</td>
              <td>Panasonic TDA/TDE, Toshiba Strata, Nortel BCM, Siemens HiPath</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="research-section">
        <h3>{L === "en" ? "Solution Catalog with Sizing and Source URLs" : "含規模建議與來源網址的方案目錄"}</h3>
        <table className="registry-table">
          <thead>
            <tr>
              <th>{L === "en" ? "Solution" : "方案"}</th>
              <th>{L === "en" ? "Vendor" : "供應商"}</th>
              <th>{L === "en" ? "Region" : "區域"}</th>
              <th>{L === "en" ? "Category" : "類別"}</th>
              <th>{L === "en" ? "Terminals" : "建議終端數"}</th>
              <th>{L === "en" ? "Cost" : "成本"}</th>
              <th>{L === "en" ? "Industry" : "適用產業"}</th>
              <th>{L === "en" ? "Source" : "來源"}</th>
            </tr>
          </thead>
          <tbody>
            {SAMPLES.map((s) => (
              <tr key={s.name}>
                <td>{s.name}</td>
                <td>{s.vendor}</td>
                <td>{String(s.country_code).toUpperCase()}</td>
                <td><span className={`category-badge ${s.lifecycle_assigned}`}>{L === "en" ? CATEGORIES.find(c => c.id === s.lifecycle_assigned)?.labelEn : CATEGORIES.find(c => c.id === s.lifecycle_assigned)?.labelZh}</span></td>
                <td>{s.recommended_terminals}</td>
                <td>{s.cost_band}</td>
                <td>{s.industry_fit}</td>
                <td>{s.resource_url ? <a href={s.resource_url}>{L === "en" ? "source" : "來源"}</a> : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="research-section">
        <h3>{L === "en" ? "Key Findings" : "主要發現"}</h3>
        <ul>
          <li><strong>{registry.length} {L === "en" ? "solutions across countries/regions" : "個方案遍及多國/地區"}</strong> — {L === "en" ? `Asia-Pacific has ${byContinent.asia_pacific || 0} entries, Europe has ${byContinent.europe || 0}, and the Americas have ${byContinent.americas || 0}.` : `亞太地區有 ${byContinent.asia_pacific || 0} 個，歐洲有 ${byContinent.europe || 0} 個，美洲有 ${byContinent.americas || 0} 個。`}</li>
          <li><strong>{byCategory.most_used_eol || 0} {L === "en" ? "solutions classified EOL" : "個方案被分類為 EOL"}</strong> — {L === "en" ? "Legacy PBX remains a migration and security risk in installed bases." : "舊式 PBX 仍是既有裝機的遷移與資安風險。"}</li>
          <li><strong>{byCategory.cutting_edge || 0} {L === "en" ? "solutions classified Cutting Edge" : "個方案被分類為前沿技術"}</strong> — {L === "en" ? "Reflects the rapid pace of cloud/API/AI communication platform innovation globally." : "反映全球雲端/API/AI 通訊平台創新的快速步伐。"}</li>
          <li>{L === "en" ? "Taiwan shows a clear bifurcation: EVOX/CHT cloud PBX for new deployments vs huge legacy installed base of Panasonic/Toshiba EOL equipment." : "台灣呈現明顯兩極化：新部署採用 EVOX/CHT 雲端總機，與龐大的 Panasonic/Toshiba EOL 設備既有安裝基礎並存。"}</li>
          <li>{L === "en" ? "The crawler-enriched catalog now includes CPaaS, open-source PBX, regional telco hosted PBX, and IoT/eSIM connectivity options for edge-device command paths." : "爬蟲增補目錄已納入 CPaaS、開源 PBX、區域電信雲端總機，以及邊緣裝置控制可用的 IoT/eSIM 連線方案。"}</li>
        </ul>
      </div>
    </div>
  );
}
