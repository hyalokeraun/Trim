# 🧠 Intelligent Enterprise Knowledge Assistant (RAG Document Q&A)

Ask questions over your own policy documents. Grounded answers with citations, plus an
"I couldn't find this in the available documents" fallback — never invented answers.

## Stack (per plan + your choices)

| Layer | Choice |
|---|---|
| LLM | Pluggable: Ollama local **or** free cloud (Gemini / Groq) via `LLM_PROVIDER` in `backend/.env` |
| Retrieval | Lightweight TF-IDF + cosine (scikit-learn, JSON persistence) — chosen over sentence-transformers/ChromaDB for reliability |
| Backend | FastAPI |
| Frontend | React (Vite) + vanilla CSS |
| Bonus | LangGraph `retrieve → grade → generate → cite` flow (`POST /api/ask-agent`) + FastMCP `search_knowledge_base` tool |

## Prerequisites

- Python 3.10+ and Node 18+
- An LLM backend — pick one in `backend/.env` (`LLM_PROVIDER`):
  - `gemini` (recommended): free key, no card, at https://aistudio.google.com/apikey → set `GEMINI_API_KEY`
  - `groq`: free key at https://console.groq.com/keys → set `GROQ_API_KEY`
  - `ollama`: install from https://ollama.com/download, then `ollama pull llama3.1` + `ollama serve`

## Quickstart

```powershell
# 1) Backend
cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000   # auto-ingests data/sample_docs on first boot

# 2) Frontend (second terminal)
cd frontend
npm install
npm run dev   # http://localhost:5173 (proxies /api -> :8000)
```

## API

| Method | Endpoint | Notes |
|---|---|---|
| POST | `/api/ask` | `{ "question": "..." }` → `{ answer, sources[], confidence, result_type }` |
| POST | `/api/ask-agent` | Same schema, runs the LangGraph agent flow |
| POST | `/api/upload` | Multipart `file` (PDF/TXT/MD) → ingestion pipeline |
| GET | `/api/documents` | Indexed files + chunk counts |
| DELETE | `/api/documents/{filename}` | Remove a document |
| POST | `/api/reindex` | Clear + re-ingest bundled sample docs |
| GET | `/api/health` | `ollama_reachable`, doc/chunk counts |

## Edge cases (per spec)

| Scenario | Behavior |
|---|---|
| No matching document | `"I couldn't find this in the available documents."` |
| Empty question | HTTP 400 prompting the user to type a question |
| Very short / ambiguous (`"leave?"`) | One clarifying question before answering |
| Ollama offline | HTTP 503 with install hint (`ollama pull llama3.1` + `ollama serve`) |

## Sample queries to try

- "How many casual leaves am I entitled to per year?" → 12 (HR_Policy.txt §4.2)
- "What is the password policy?" → 12 chars, MFA… (IT_Security_Policy.txt §2.1)
- "Can I work from home on Fridays?" → yes, conditions (Remote_Work_Policy.txt §2.1)
- "What is the capital of France?" → not-found fallback
- "leave?" → clarifying question

## MCP tool (bonus)

```powershell
cd backend
fastmcp run app/mcp/server.py
# tool: search_knowledge_base(query, top_k) -> { answer, sources }
# tool: list_documents() -> { documents, total_chunks }
```

## Project layout

```
backend/app/{main,config}.py  routers/{ask,upload,documents}.py
          services/{ingestion,retriever,llm,vectorstore}.py
          agent/graph.py  mcp/server.py  models/schemas.py
backend/data/sample_docs/*.txt   backend/vector_store/chunks.json
frontend/src/{App,main,api}.jsx  components/{ChatWindow,MessageBubble,SourceSnippet,DocumentUpload,Sidebar}.jsx
```
