import "./globals.css";
import { getLang } from "../i18n";

const LANG = getLang();

export const metadata = {
  title:
    LANG === "en"
      ? "PBX Market Estimation & VoIP Trend Analysis"
      : "PBX 市場預測與 VoIP 趨勢分析",
  description:
    LANG === "en"
      ? "Quantitative forecasting of PBX market decline and VoIP adoption across global markets."
      : "全球 PBX 市場衰退與 VoIP 採用率的量化預測分析。",
};

export default function RootLayout({ children }) {
  return (
    <html lang={LANG === "en" ? "en" : "zh-TW"}>
      <body>{children}</body>
    </html>
  );
}
