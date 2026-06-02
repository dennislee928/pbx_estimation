export default function Sidebar({ reports, active, onSelect }) {
  return (
    <aside className="sidebar">
      <ul className="sidebar-nav">
        {reports.map((r) => (
          <li
            key={r.id}
            className={`sidebar-item${r.id === active ? " active" : ""}`}
            onClick={() => onSelect(r.id)}
          >
            {r.label}
          </li>
        ))}
      </ul>
    </aside>
  );
}
