import { useCallback, useEffect, useState } from 'react';
import { BookOpenText, Bot, X } from 'lucide-react';
import ChatWindow from './components/ChatWindow.jsx';
import Sidebar from './components/Sidebar.jsx';
import { listDocuments, deleteDocument, fetchHealth } from './api.js';

export default function App() {
  const [docs, setDocs] = useState([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [health, setHealth] = useState(null);
  const [toasts, setToasts] = useState([]);
  const [useAgent, setUseAgent] = useState(false);

  const pushToast = useCallback((text) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const d = await listDocuments();
      setDocs(d.documents || []);
      setTotalChunks(d.total_chunks || 0);
    } catch (e) {
      pushToast(e.message);
    }
    try {
      setHealth(await fetchHealth());
    } catch {
      setHealth({ ollama_reachable: false, ollama_model: '' });
    }
  }, [pushToast]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleDelete(filename) {
    try {
      await deleteDocument(filename);
      pushToast(`Deleted ${filename}`);
      refresh();
    } catch (e) {
      pushToast(e.message);
    }
  }

  return (
    <div className="app">
      <header className="topbar glass">
        <div className="brand">
          <BookOpenText size={20} />
          <div>
            <h1>Knowledge Assistant</h1>
            <p>Enterprise RAG Q&A · grounded answers with citations</p>
          </div>
        </div>
        <label className="agent-toggle" title="Route questions through the LangGraph agent flow">
          <Bot size={14} />
          <input type="checkbox" checked={useAgent} onChange={(e) => setUseAgent(e.target.checked)} />
          LangGraph agent
        </label>
      </header>

      <main className="layout">
        <Sidebar
          docs={docs}
          totalChunks={totalChunks}
          health={health}
          onUploaded={refresh}
          onDelete={handleDelete}
          pushToast={pushToast}
        />
        <section className="main glass">
          <ChatWindow useAgent={useAgent} pushToast={pushToast} />
        </section>
      </main>

      <footer className="foot">Powered by Ollama + TF-IDF retrieval · LangGraph agent + MCP tool included</footer>

      <div className="toasts">
        {toasts.map((t) => (
          <div key={t.id} className="toast">
            <span>{t.text}</span>
            <button onClick={() => setToasts((x) => x.filter((y) => y.id !== t.id))}>
              <X size={13} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
