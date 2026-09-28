import { useRef, useState } from 'react';
import { UploadCloud, FileUp } from 'lucide-react';
import { uploadDocument } from '../api.js';

export default function DocumentUpload({ onUploaded, pushToast }) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  async function handleFiles(files) {
    const list = Array.from(files || []);
    if (!list.length) return;
    setUploading(true);
    try {
      for (const f of list) {
        const res = await uploadDocument(f);
        pushToast?.(`Ingested ${res.filename} (${res.chunks_created} chunks)`);
      }
      onUploaded?.();
    } catch (e) {
      pushToast?.(e.message);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  return (
    <div className="upload-panel">
      <div
        className={`dropzone ${dragOver ? 'over' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => fileRef.current?.click()}
      >
        <UploadCloud size={28} />
        <p>{uploading ? 'Uploading…' : 'Drop PDF / TXT / MD here'}</p>
        <span>or click to browse</span>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".pdf,.txt,.md"
          hidden
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>
      <button className="upload-btn" disabled={uploading} onClick={() => fileRef.current?.click()}>
        <FileUp size={14} /> {uploading ? 'Uploading…' : 'Upload documents'}
      </button>
    </div>
  );
}
