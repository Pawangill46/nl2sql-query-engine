import { useState } from 'react'
import Sidebar from './components/Sidebar'
import UploadZone from './components/UploadZone'
import ResultCard from './components/ResultCard'
import { uploadFile, askQuestion } from './api'
import { ArrowRight, Loader2 } from 'lucide-react'

export default function App() {
  const [tables, setTables] = useState({})
  const [loadedFileName, setLoadedFileName] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState(null) // { type: 'success' | 'error', message }

  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)
  const [history, setHistory] = useState([])

  async function handleUpload(file) {
    setUploading(true)
    setUploadStatus(null)
    try {
      const data = await uploadFile(file)
      setTables(data.tables || {})
      setLoadedFileName(file.name)
      setUploadStatus({ type: 'success', message: `Schema loaded: ${Object.keys(data.tables || {}).join(', ')}` })
    } catch (err) {
      setUploadStatus({ type: 'error', message: err.message })
    } finally {
      setUploading(false)
    }
  }

  async function handleAsk(q) {
    const query = (q ?? question).trim()
    if (!query) return
    setAsking(true)
    try {
      const outcome = await askQuestion(query)
      setHistory((h) => [{ question: query, ...outcome }, ...h])
      setQuestion('')
    } catch (err) {
      setHistory((h) => [{ question: query, sql: null, result: null, error: err.message }, ...h])
    } finally {
      setAsking(false)
    }
  }

  const dataLoaded = Object.keys(tables).length > 0

  return (
    <div className="app">
      <Sidebar tables={tables} history={history} onSelectHistory={(q) => handleAsk(q)} />

      <main className="main">
        <div className="hero">
          <h1>Query console</h1>
          <p>Upload a spreadsheet, ask in plain English, get real answers with the SQL to prove it.</p>
        </div>

        <UploadZone onUpload={handleUpload} loading={uploading} loadedFileName={loadedFileName} />

        {uploadStatus && (
          <div className={`status-banner ${uploadStatus.type}`}>{uploadStatus.message}</div>
        )}

        <div className="console-prompt">
          <span className="caret">&gt;</span>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
            placeholder={dataLoaded ? 'ask a question about your data...' : 'upload a file first'}
            disabled={!dataLoaded || asking}
          />
          <button
            className="btn btn-primary"
            onClick={() => handleAsk()}
            disabled={!dataLoaded || asking || !question.trim()}
          >
            {asking ? <Loader2 size={14} className="spin" /> : <ArrowRight size={14} />}
          </button>
        </div>

        <div className="feed">
          {history.length === 0 ? (
            <div className="empty-feed">
              {dataLoaded
                ? 'no queries yet — ask something above'
                : 'waiting for data...'}
            </div>
          ) : (
            history.map((entry, i) => <ResultCard key={i} entry={entry} />)
          )}
        </div>
      </main>
    </div>
  )
}
