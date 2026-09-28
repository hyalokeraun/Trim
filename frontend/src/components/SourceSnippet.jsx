import { useState } from 'react';
import { ChevronDown, FileText } from 'lucide-react';

/** Expandable "View Source" snippet showing exactly where the answer came from. */
export default function SourceSnippet({ source, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="source-card">
      <button className="source-toggle" onClick={() => setOpen((v) => !v)}>
        <FileText size={14} />
        <span>
          Source: {source.document}
          {source.section && source.section !== 'N/A' ? ` §${source.section}` : ''}
        </span>
        <ChevronDown size={14} className={`chev ${open ? 'rot' : ''}`} />
      </button>
      {open && (
        <div className="source-body">
          <div className="source-meta">
            <span>{source.document}</span>
            {source.section && source.section !== 'N/A' && <span>Section {source.section}</span>}
            {typeof source.score === 'number' && <span>relevance {source.score.toFixed(2)}</span>}
          </div>
          <p className="source-snippet">{source.snippet}</p>
        </div>
      )}
    </div>
  );
}
