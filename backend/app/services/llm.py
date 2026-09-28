"""Pluggable LLM integration: local Ollama OR free cloud APIs (Gemini / Groq).

Selected via LLM_PROVIDER in .env. All failures raise LLMError (with an
actionable message) so the API can return a clear 503. No API keys are
hardcoded — they come from backend/.env only.
"""
import httpx

from app.config import (
    SYSTEM_PROMPT, LLM_TIMEOUT_S,
    LLM_PROVIDER, OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT_S,
    GEMINI_API_KEY, GEMINI_MODEL, GROQ_API_KEY, GROQ_MODEL,
)


class LLMError(RuntimeError):
    pass


class OllamaUnavailable(LLMError):
    pass


OLLAMA_HINT = (
    "Ollama is not reachable at {host}. Either start it "
    "(ollama serve + ollama pull {model}) or switch to a free cloud LLM: "
    "set LLM_PROVIDER=gemini in backend/.env with a free key from "
    "https://aistudio.google.com/apikey"
)
GEMINI_KEY_HINT = (
    "GEMINI_API_KEY is missing. Get a free key (no card) at "
    "https://aistudio.google.com/apikey and set GEMINI_API_KEY in backend/.env"
)
GROQ_KEY_HINT = (
    "GROQ_API_KEY is missing. Get a free key at "
    "https://console.groq.com/keys and set GROQ_API_KEY in backend/.env"
)


def _context_block(chunks) -> str:
    parts = []
    for c in chunks:
        parts.append(
            f"[Source: {c['source']}, Section: {c.get('section', 'N/A')}]\n{c['text']}"
        )
    return "\n\n---\n\n".join(parts)


def _history_block(history) -> str:
    if not history:
        return ""
    lines = []
    for turn in (history or [])[-6:]:
        role = (turn.get("role") if isinstance(turn, dict) else getattr(turn, "role", "user")) or "user"
        text = (turn.get("content") if isinstance(turn, dict) else getattr(turn, "content", ""))
        text = (text or "")[:400]
        who = "User" if role == "user" else "Assistant"
        lines.append(f"{who}: {text}")
    return "\n".join(lines)


def _prompt(question: str, chunks, history=None) -> str:
    base = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Context excerpts:\n{_context_block(chunks)}\n\n"
    )
    hist = _history_block(history)
    if hist:
        base += f"Conversation so far (for reference resolution only):\n{hist}\n\n"
    return base + f"Question: {question}\nAnswer (with source citations):"


# ---------------- Ollama (local) ----------------

def _generate_ollama(prompt: str) -> str:
    try:
        import ollama as ollama_lib  # type: ignore
        client = ollama_lib.Client(host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT_S)
        resp = client.generate(model=OLLAMA_MODEL, prompt=prompt)
        text = resp.get("response", "") if isinstance(resp, dict) else getattr(resp, "response", "")
        if text and text.strip():
            return text.strip()
    except Exception:
        pass  # fall through to HTTP
    try:
        r = httpx.post(
            f"{OLLAMA_HOST.rstrip('/')}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT_S,
        )
        r.raise_for_status()
        text = r.json().get("response", "")
        if text.strip():
            return text.strip()
    except Exception as e:
        raise OllamaUnavailable(OLLAMA_HINT.format(host=OLLAMA_HOST, model=OLLAMA_MODEL)) from e
    raise OllamaUnavailable(OLLAMA_HINT.format(host=OLLAMA_HOST, model=OLLAMA_MODEL))


def check_ollama() -> bool:
    try:
        r = httpx.get(f"{OLLAMA_HOST.rstrip('/')}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ---------------- Gemini (free tier, REST) ----------------

def _generate_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise LLMError(GEMINI_KEY_HINT)
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent")
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 512},
    }
    try:
        r = httpx.post(url, params={"key": GEMINI_API_KEY}, json=body, timeout=LLM_TIMEOUT_S)
    except Exception as e:
        raise LLMError(f"Could not reach Gemini API: {e}") from e
    if r.status_code == 400:
        raise LLMError(f"Gemini rejected the request (check GEMINI_MODEL={GEMINI_MODEL}): {r.text[:200]}")
    if r.status_code == 429:
        raise LLMError("Gemini free-tier quota exceeded. Wait a minute and retry.")
    if r.status_code in (401, 403):
        raise LLMError("Gemini API key invalid. Regenerate one at https://aistudio.google.com/apikey")
    if r.status_code != 200:
        raise LLMError(f"Gemini API error ({r.status_code}): {r.text[:200]}")
    try:
        cands = r.json().get("candidates", [])
        parts = cands[0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
    except Exception:
        text = ""
    if not text:
        raise LLMError("Gemini returned an empty/blocked response. Try rephrasing the question.")
    return text


def check_gemini() -> bool:
    if not GEMINI_API_KEY:
        return False
    try:
        r = httpx.get("https://generativelanguage.googleapis.com/v1beta/models",
                      params={"key": GEMINI_API_KEY}, timeout=10)
        return r.status_code == 200
    except Exception:
        return False


# ---------------- Groq (free tier, OpenAI-compatible) ----------------

def _generate_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        raise LLMError(GROQ_KEY_HINT)
    try:
        r = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 512,
            },
            timeout=LLM_TIMEOUT_S,
        )
    except Exception as e:
        raise LLMError(f"Could not reach Groq API: {e}") from e
    if r.status_code == 401:
        raise LLMError("Groq API key invalid. Get one at https://console.groq.com/keys")
    if r.status_code == 429:
        raise LLMError("Groq rate limit hit. Wait a few seconds and retry.")
    if r.status_code != 200:
        raise LLMError(f"Groq API error ({r.status_code}): {r.text[:200]}")
    text = (r.json()["choices"][0]["message"].get("content") or "").strip()
    if not text:
        raise LLMError("Groq returned an empty response. Retry the question.")
    return text


def check_groq() -> bool:
    if not GROQ_API_KEY:
        return False
    try:
        r = httpx.get("https://api.groq.com/openai/v1/models",
                      headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, timeout=10)
        return r.status_code == 200
    except Exception:
        return False


# ---------------- dispatch ----------------

def generate_answer(question: str, chunks, history=None) -> str:
    provider = (LLM_PROVIDER or "ollama").lower()
    prompt = _prompt(question, chunks, history)
    if provider == "gemini":
        return _generate_gemini(prompt)
    if provider == "groq":
        return _generate_groq(prompt)
    if provider == "ollama":
        return _generate_ollama(prompt)
    raise LLMError(f"Unknown LLM_PROVIDER='{LLM_PROVIDER}'. Use ollama, gemini, or groq.")


def check_llm() -> tuple[str, bool]:
    """Return (provider, ready)."""
    provider = (LLM_PROVIDER or "ollama").lower()
    if provider == "gemini":
        return provider, check_gemini()
    if provider == "groq":
        return provider, check_groq()
    return "ollama", check_ollama()
