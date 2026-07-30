import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from 'recharts'
import { AlertTriangle, RotateCcw } from 'lucide-react'

function isNumeric(val) {
  return typeof val === 'number'
}

export default function ResultCard({ entry }) {
  const { question, sql, result, error, attempts } = entry
  const rows = result || []
  const columns = rows.length > 0 ? Object.keys(rows[0]) : []

  // Only chart when there's a label column + one numeric column, and more
  // than one row -- a single aggregate value (like AVG) reads better as
  // a number in a table than a one-bar chart.
  const numericCols = columns.filter((c) => rows.every((r) => isNumeric(r[c])))
  const labelCol = columns.find((c) => !numericCols.includes(c))
  const canChart = rows.length > 1 && numericCols.length >= 1 && labelCol

  return (
    <div className={`result-card ${error ? 'errored' : ''}`}>
      <div className="result-card-header">
        <p className="result-question">{question}</p>
        {sql && <div className="result-sql">{sql}</div>}
        <div className="result-meta">
          {attempts && <span>{attempts} attempt{attempts > 1 ? 's' : ''}</span>}
          {attempts > 1 && (
            <span className="retry-flag">
              <RotateCcw size={10} style={{ verticalAlign: '-1px', marginRight: 3 }} />
              self-corrected
            </span>
          )}
          {rows.length > 0 && <span>{rows.length} row{rows.length !== 1 ? 's' : ''}</span>}
        </div>
      </div>

      <div className="result-body">
        {error && !rows.length ? (
          <div className="result-error">
            <AlertTriangle size={13} style={{ verticalAlign: '-2px', marginRight: 6 }} />
            {error}
          </div>
        ) : (
          <>
            <div className="result-table-wrap">
              <table className="result-table">
                <thead>
                  <tr>
                    {columns.map((c) => (
                      <th key={c}>{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <tr key={i}>
                      {columns.map((c) => (
                        <td key={c}>{String(row[c])}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {canChart && (
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={rows}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2a3162" vertical={false} />
                    <XAxis
                      dataKey={labelCol}
                      tick={{ fill: '#8890bd', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                      axisLine={{ stroke: '#2a3162' }}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: '#8890bd', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        background: '#0e1226',
                        border: '1px solid #2a3162',
                        borderRadius: 8,
                        fontFamily: 'JetBrains Mono',
                        fontSize: 12,
                      }}
                      cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                    />
                    <Bar dataKey={numericCols[0]} fill="#35d0b0" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
