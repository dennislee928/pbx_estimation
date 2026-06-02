export default function ReportViewer({ report }) {
  return (
    <iframe
      key={report.id}
      className="report-frame"
      src={report.file}
      title={report.label}
      sandbox="allow-scripts allow-same-origin allow-forms"
    />
  );
}
