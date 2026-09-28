import { useEffect, useRef, useState } from 'react';
import { SendHorizonal, Sparkles } from 'lucide-react';
import MessageBubble from './MessageBubble.jsx';
import { askQuestion } from '../api.js';

const STARTERS = [
  'How many casual leaves am I entitled to per year?',
  'What is the password policy?',
  'Can I work from home on Fridays?',
  'How do I submit a travel reimbursement claim?',
];

export default function ChatWindow({ useAgent, pushToast }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: "Hi! I'm your enterprise knowledge assistant. Ask me anything about company policies — I'll answer with source citations. Try a starter question below.",
      sources: [],
      result_type: 'exact',
      confidence: 0,
    },
  ]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, busy]);

  async function send(text) {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    if (!q) {
      pushToast?.('Please type a question first.');
      return;
    }
    setInput('');
    setMessages((m) => [...m, { role: 'user', text: q }]);
    // context-driven chat: send recent turns so follow-ups ("those?", "and sick leave?") resolve
    const history = messages
      .filter((m) => !m.loading && m.text)
      .slice(-6)
      .map((m) => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.text.slice(0, 600) }));
    setBusy(true);
    try {
      const data = await askQuestion(q, useAgent, history);
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          text: data.answer,
          sources: data.sources || [],
          confidence: data.confidence || 0,
          result_type: data.result_type || 'exact',
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', text: `⚠️ ${e.message}`, sources: [], result_type: 'exact', confidence: 0 },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat">
      <div className="chat-log">
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {busy && <MessageBubble message={{ role: 'assistant', loading: true }} />}
        <div ref={bottomRef} />
      </div>

      {messages.length <= 1 && (
        <div className="starters">
          {STARTERS.map((s) => (
            <button key={s} className="starter" onClick={() => send(s)} disabled={busy}>
              <Sparkles size={13} /> {s}
            </button>
          ))}
        </div>
      )}

      <div className="composer">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Ask a question about policies, leaves, security…"
          disabled={busy}
        />
        <button className="send" onClick={() => send()} disabled={busy || !input.trim()}>
          <SendHorizonal size={16} /> Send
        </button>
      </div>
    </div>
  );
}
