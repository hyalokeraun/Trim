"""Central settings & constants. Loaded from .env with sane defaults."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
APP_DIR = Path(__file__).resolve().parent          # backend/app

OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1")
OLLAMA_TIMEOUT_S: int = int(os.getenv("OLLAMA_TIMEOUT_S", "120"))

# Free cloud LLM providers (no card required; key goes in .env, never commit it)
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
LLM_TIMEOUT_S: int = int(os.getenv("LLM_TIMEOUT_S", "60"))

TOP_K: int = int(os.getenv("TOP_K", "5"))
RELEVANCE_THRESHOLD: float = float(os.getenv("RELEVANCE_THRESHOLD", "0.08"))

CHUNK_SIZE_CHARS: int = int(os.getenv("CHUNK_SIZE_CHARS", "2000"))
CHUNK_OVERLAP_CHARS: int = int(os.getenv("CHUNK_OVERLAP_CHARS", "200"))

VECTOR_STORE_DIR: Path = (BASE_DIR / os.getenv("VECTOR_STORE_DIR", "./vector_store").lstrip("./")).resolve()
SAMPLE_DOCS_DIR: Path = (BASE_DIR / os.getenv("SAMPLE_DOCS_DIR", "./data/sample_docs").lstrip("./")).resolve()

BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}

NOT_FOUND_MESSAGE = "I couldn't find this in the available documents."
EMPTY_QUESTION_MESSAGE = "Please type a question so I can search the documents for you."

SYSTEM_PROMPT = """You are an enterprise knowledge assistant. Answer ONLY using the provided context excerpts.
Rules:
1. If the context contains the answer, give a concise answer (1-4 sentences).
2. Always cite the source document and section, e.g. (Source: HR_Policy.txt, Section 4.2).
3. If the context does NOT contain the answer, reply EXACTLY: "I couldn't find this in the available documents."
4. Never invent facts, numbers, or policies not present in the context.
5. If the question is ambiguous, ask exactly ONE clarifying question instead of answering."""
