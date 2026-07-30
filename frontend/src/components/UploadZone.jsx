import { useRef, useState } from 'react'
import { UploadCloud, Loader2 } from 'lucide-react'

export default function UploadZone({ onUpload, loading, loadedFileName }) {
  const inputRef = useRef(null)
  const [dragActive, setDragActive] = useState(false)

  function handleFiles(files) {
    if (files && files[0]) {
      onUpload(files[0])
    }
  }

  return (
    <div
      className={`upload-zone ${dragActive ? 'drag-active' : ''}`}
      onDragOver={(e) => {
        e.preventDefault()
        setDragActive(true)
      }}
      onDragLeave={() => setDragActive(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragActive(false)
        handleFiles(e.dataTransfer.files)
      }}
    >
      <div className="upload-zone-icon">
        {loading ? <Loader2 size={20} className="spin" /> : <UploadCloud size={20} />}
      </div>
      <div className="upload-zone-text">
        <div className="title">
          {loadedFileName ? `Loaded: ${loadedFileName}` : 'Drop an Excel or CSV file here'}
        </div>
        <div className="sub">
          {loading ? 'building schema...' : '.xlsx, .xls, or .csv — or click to browse'}
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.xls,.csv"
        className="file-input-hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <button
        className="btn btn-ghost"
        disabled={loading}
        onClick={() => inputRef.current?.click()}
      >
        Browse
      </button>
    </div>
  )
}
