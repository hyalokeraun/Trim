import { FileText, Trash2, RefreshCw } from 'lucide-react';
import DocumentUpload from './DocumentUpload.jsx';

export default function Sidebar({ docs, totalChunks, onUploaded, onDelete, health, pushToast }) {
  return (
    <aside className="sidebar glass">
      <h2>Documents</h2>
      <DocumentUpload onUploaded={onUploaded} pushToast={pushToast} />

      <div className="doc-meta">
        <span>{docs.length} file(s)</span>
        <span>{totalChunks} chunk(s)</span>
      </div>

      <ul className="doc-list">
        {docs.map((d) => (
          <li key={d.filename} title={`${d.chunks} chunks · ${d.chars} chars`}>
            <FileText size={14} />
            <span className="doc-name">{d.filename}</span>
            <span className="doc-chunks">{d.chunks}</span>
            <button
              className="icon-btn danger"
              title={`Delete ${d.filename}`}
              onClick={() => onDelete(d.filename)}
            >
              <Trash2 size={13} />
            </button>
          </li>
        ))}
        {docs.length === 0 && <li className="empty">No documents indexed yet.</li>}
      </ul>

      <div className="health">
        <span className={`pill ${health?.llm_ready ?? health?.ollama_reachable ? 'ok' : 'bad'}`}>
          {health?.llm_provider ?? 'ollama'} {health?.llm_ready ?? health?.ollama_reachable ? 'ready' : 'not configured'}
        </span>
        {health?.ollama_model && <span className="model">{health.ollama_model}</span>}
        <button
          className="icon-btn"
          title="Refresh document list"
          onClick={onUploaded}
        >
          <RefreshCw size={13} />
        </button>
      </div>
    </aside>
  );
}
