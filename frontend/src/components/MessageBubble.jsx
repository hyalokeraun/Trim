import ReactMarkdown from 'react-markdown';
import { Bot, User } from 'lucide-react';
import SourceSnippet from './SourceSnippet.jsx';

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  return (
    <div className={`msg-row ${isUser ? 'user' : 'bot'}`}>
      <div className="avatar">{isUser ? <User size={16} /> : <Bot size={16} />}</div>
      <div className={`bubble ${isUser ? 'user' : 'bot'} ${message.result_type || ''}`}>
        {message.loading ? (
          <span className="typing">
            <span className="dot" /><span className="dot" /><span className="dot" />
          </span>
        ) : isUser ? (
          <p>{message.text}</p>
        ) : (
          <>
            <div className="md">
              <ReactMarkdown>{message.text}</ReactMarkdown>
            </div>
            {message.confidence > 0 && (
              <div className="conf">confidence {message.confidence.toFixed(2)}</div>
            )}
            {message.sources?.length > 0 && (
              <div className="sources">
                {message.sources.map((s, i) => (
                  <SourceSnippet key={i} source={s} defaultOpen={i === 0} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
