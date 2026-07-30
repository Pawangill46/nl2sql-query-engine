import { Database, History, Terminal } from 'lucide-react'

export default function Sidebar({ tables, history, onSelectHistory }) {
  const tableNames = Object.keys(tables || {})

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <Terminal size={18} strokeWidth={2.5} />
        </div>
        <div>
          <div className="brand-text">NL2SQL Console</div>
          <div className="brand-sub">ask your data anything</div>
        </div>
      </div>

      <div>
        <div className="sidebar-section-label">
          <Database size={12} /> Schema
        </div>
        {tableNames.length === 0 ? (
          <div className="empty-hint">No data loaded yet. Upload a file to see its tables here.</div>
        ) : (
          tableNames.map((name) => (
            <div key={name}>
              <div className="table-chip">
                <span className="dot" />
                {name}
              </div>
              <ul className="column-list">
                {(tables[name] || []).map((col) => (
                  <li key={col.name}>
                    {col.name} <span style={{ opacity: 0.6 }}>({col.type})</span>
                  </li>
                ))}
              </ul>
            </div>
          ))
        )}
      </div>

      <div>
        <div className="sidebar-section-label">
          <History size={12} /> Recent queries
        </div>
        {(!history || history.length === 0) ? (
          <div className="empty-hint">Your question history will show up here.</div>
        ) : (
          history.slice(0, 12).map((entry, i) => (
            <div
              key={i}
              className="history-item"
              onClick={() => onSelectHistory(entry.question)}
              title="Click to re-ask this"
            >
              {entry.question}
            </div>
          ))
        )}
      </div>
    </aside>
  )
}
