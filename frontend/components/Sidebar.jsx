import { t } from "../i18n";

export default function Sidebar({ groups, active, onSelect }) {
  return (
    <aside className="sidebar">
      {groups.map((group) => (
        <div key={group.section}>
          <div className="sidebar-section-label">{t(group.section)}</div>
          <ul className="sidebar-nav">
            {group.items.map((item) => (
              <li
                key={item.id}
                className={`sidebar-item${item.id === active ? " active" : ""}`}
                onClick={() => onSelect(item.id)}
              >
                {item.label}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </aside>
  );
}
