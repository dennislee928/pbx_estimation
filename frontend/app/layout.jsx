import "./globals.css";

export const metadata = {
  title: "PBX 市場預測與 VoIP 趨勢分析",
  description:
    "Quantitative forecasting of PBX market decline and VoIP adoption across 12+ countries.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="zh-TW">
      <body>{children}</body>
    </html>
  );
}
