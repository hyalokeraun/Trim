/** Tiny API client. Uses Vite proxy (/api -> localhost:8000) in dev. */
const BASE = '';

async function parseError(res) {
  try {
    const data = await res.json();
    return data.detail || data.message || `Request failed (${res.status})`;
  } catch {
    return `Request failed (${res.status})`;
  }
}

export async function askQuestion(question, useAgent = false, history = []) {
  const res = await fetch(`${BASE}/api/${useAgent ? 'ask-agent' : 'ask'}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, history }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function uploadDocument(file, onProgress) {
  const form = new FormData();
  form.append('file', file);
  // fetch has no upload progress; simulate indeterminate state via onProgress(true)
  onProgress?.(true);
  try {
    const res = await fetch(`${BASE}/api/upload`, { method: 'POST', body: form });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json();
  } finally {
    onProgress?.(false);
  }
}

export async function listDocuments() {
  const res = await fetch(`${BASE}/api/documents`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function deleteDocument(filename) {
  const res = await fetch(`${BASE}/api/documents/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch(`${BASE}/api/health`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}
