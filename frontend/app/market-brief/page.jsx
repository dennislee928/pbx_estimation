"use client";

import { t, getLang } from "../../i18n";

const L = getLang();

export default function MarketBriefPage() {
  return (
    <div className="research-page">
      <h2>{t("marketBrief")}</h2>
      <p className="subtitle">
        {L === "en"
          ? "Verified and structured market research on the global PBX transition to VoIP, covering Taiwan SME digital transformation, regional adoption patterns, security concerns, and regulatory drivers."
          : "經由產品研究與技術研究功能驗證與篩選後的市場研究摘要，涵蓋台灣中小企業數位轉型、全球區域 VoIP 採用模式、資安風險及法規驅動因素。"}
      </p>

      <div className="research-section">
        <h3>{L === "en" ? "1. Taiwan SME Digital Transformation" : "1. 台灣中小企業數位轉型概況"}</h3>
        <p>
          {L === "en"
            ? 'According to MIC (資策會產業情報研究所), IDC Taiwan, and EVOX market observations: An estimated 60-70% of Taiwan\'s 1.6 million SMEs still rely on on-premise PBX hardware, with most systems deployed 7-10+ years ago. Major vendors Panasonic, Toshiba, and NEC have exited or reduced PBX investment. Avaya underwent restructuring and pivoted to cloud. Many deployed systems are effectively in EOL/EOS status, maintained by local SI vendors using second-hand spare parts.'
            : '根據資策會（MIC）、IDC Taiwan 與 EVOX 市場觀察：台灣約 160 萬家中小企業中，估計有 60-70% 仍依賴在地端硬體總機，多數已建置超過 7-10 年。Panasonic 已宣布退出企業通訊交換機市場，Toshiba 早已退出，Avaya 經歷重整並轉向雲端，多數在役設備實質處於 EOL/EOS 狀態，僅靠國內 SI 廠商以二手備品進行維護。'}
        </p>
      </div>

      <div className="research-section">
        <h3>{L === "en" ? "2. Key Drivers" : "2. 關鍵驅動因素"}</h3>
        <ul>
          <li>
            <strong>{L === "en" ? "Hybrid Work & Mobility" : "混合辦公與行動化"}:</strong>{" "}
            {L === "en"
              ? "Post-pandemic hybrid work requires mobile app extensions and softphones. Legacy EOL PBX cannot integrate these, driving migration to UCaaS."
              : "後疫情混合辦公需要手機 App 分機與軟體電話。傳統 EOL PBX 無法支援，促使企業升級至 UCaaS。"}
          </li>
          <li>
            <strong>{L === "en" ? "API Integration & Digital Transformation" : "數位轉型與 API 串接"}:</strong>{" "}
            {L === "en"
              ? "CRM, Microsoft Teams, LINE, Slack integration requires software-defined communication APIs that legacy PBX/IVR cannot provide."
              : "CRM、Microsoft Teams、LINE、Slack 等整合需要軟體定義的通訊 API，老舊 PBX/IVR 無法滿足。"}
          </li>
          <li>
            <strong>{L === "en" ? "Supply Chain Disruption" : "供應鏈斷裂"}:</strong>{" "}
            {L === "en"
              ? "EOL means no new hardware, no replacement parts from OEMs. Second-hand spare parts market is unreliable for B2B enterprise products."
              : "EOL 意味無新硬體、無原廠零件。二手備品市場對 B2B 企業產品而言不可靠。"}
          </li>
          <li>
            <strong>{L === "en" ? "PSTN Switch-off" : "PSTN 退場"}:</strong>{" "}
            {L === "en"
              ? "BEREC reports EU-wide copper switch-off accelerates. UK BT PSTN shutdown Jan 2027, Germany 2018, Spain 2025. Physical TDM/analog infrastructure loss fundamentally disconnects legacy systems."
              : "BEREC 報告歐盟全面銅線退場加速。英國 BT PSTN 2027 年 1 月關閉，德國 2018，西班牙 2025。實體 TDM/類比基礎設施的消失從根本上斷開老舊系統。"}
          </li>
        </ul>
      </div>

      <div className="research-section">
        <h3>{L === "en" ? "3. Regional VoIP Adoption" : "3. 五大洲 VoIP 轉型進程"}</h3>
        <table className="registry-table">
          <thead>
            <tr>
              <th>{L === "en" ? "Region" : "洲別"}</th>
              <th>{L === "en" ? "Pace" : "進程"}</th>
              <th>{L === "en" ? "Key Dynamics" : "主要動態"}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{L === "en" ? "Europe" : "歐洲"}</td>
              <td>{L === "en" ? "Fast (policy-driven)" : "極快（政策驅動）"}</td>
              <td>{L === "en" ? "PSTN switch-off roadmaps from UK, Germany, France, Spain force SIP Trunk/UCaaS migration." : "英國、德國、法國、西班牙的 PSTN 退場路線圖強制 SIP Trunk/UCaaS 遷移。"}</td>
            </tr>
            <tr>
              <td>{L === "en" ? "North America" : "北美洲"}</td>
              <td>{L === "en" ? "Fast (market-driven)" : "極快（市場驅動）"}</td>
              <td>{L === "en" ? "High SaaS/cloud adoption. On-prem PBX <30% market share. Teams Phone, Zoom Phone, RingCentral dominant." : "SaaS/雲端接受度高。地端 PBX 佔有率 <30%。Teams Phone、Zoom Phone、RingCentral 為主流。"}</td>
            </tr>
            <tr>
              <td>{L === "en" ? "Asia-Pacific" : "亞太"}</td>
              <td>{L === "en" ? "Polarized" : "高度兩極化"}</td>
              <td>{L === "en" ? "Japan/Singapore/AU in All-IP era. SE Asia + India still heavily dependent on second-hand TDM/hybrid PBX." : "日本/新加坡/澳洲已進入 All-IP 時代。東南亞與印度仍大量依賴二手 TDM/混合式 PBX。"}</td>
            </tr>
            <tr>
              <td>{L === "en" ? "Latin America" : "拉丁美洲"}</td>
              <td>{L === "en" ? "Stable (mobile-first)" : "穩定成長"}</td>
              <td>{L === "en" ? "Long PBX replacement cycles. WhatsApp Business API used as IVR alternative." : "PBX 更新週期長。WhatsApp Business API 被用作 IVR 替代方案。"}</td>
            </tr>
            <tr>
              <td>{L === "en" ? "Africa" : "非洲"}</td>
              <td>{L === "en" ? "Leapfrog (mobile)" : "跳躍式發展"}</td>
              <td>{L === "en" ? "Low fixed-line penetration, direct-to-mobile VoIP/cloud communication adoption." : "固網普及率低，直接進入行動 VoIP 與雲端通訊。"}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="research-section">
        <h3>{L === "en" ? "4. Security Concerns" : "4. 資安風險"}</h3>
        <ul>
          <li><strong>{L === "en" ? "EDR/SIEM Blind Spots" : "EDR/SIEM 防禦盲區"}:</strong> {L === "en" ? "EOL PBX runs legacy RTOS/embedded Linux. Cannot install security agents. No syslog over TLS support." : "EOL PBX 運行老舊 RTOS/嵌入式 Linux。無法安裝安全代理。不支援 Syslog over TLS。"}</li>
          <li><strong>{L === "en" ? "Forever-Day Vulnerabilities" : "永久漏洞"}:</strong> {L === "en" ? "No firmware patches for known CVEs (command injection, buffer overflow on web GUI, SIP stack)." : "沒有韌體修補已知 CVE（命令注入、Web GUI 緩衝區溢位、SIP 堆疊漏洞）。"}</li>
          <li><strong>{L === "en" ? "Plaintext Protocols" : "明文傳輸"}:</strong> {L === "en" ? "SIP on UDP 5060, unencrypted RTP. ARP spoofing enables call interception and DTMF sniffing." : "UDP 5060 上明文的 SIP，未加密的 RTP。ARP Spoofing 可攔截通話與 DTMF 訊號。"}</li>
          <li><strong>{L === "en" ? "IAM Gaps" : "身分驗證斷層"}:</strong> {L === "en" ? "Static passwords/PIN, no SAML/OIDC, no MFA. ATA shadow IT risk with default credentials." : "靜態密碼/PIN，不支援 SAML/OIDC，無 MFA。ATA 淪為 Shadow IT 風險。"}</li>
        </ul>
        <p className="source-cite">
          {L === "en"
            ? "References: CISA Bad Practices, NIST SP 800-53 (SA-22), OWASP IoT Top 10"
            : "參考來源：CISA Bad Practices、NIST SP 800-53 (SA-22)、OWASP IoT Top 10"}
        </p>
      </div>
    </div>
  );
}
