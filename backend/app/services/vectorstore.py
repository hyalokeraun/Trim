"""Lightweight TF-IDF vector store (user chose TF-IDF over sentence-transformers/ChromaDB).

- Chunks persisted to VECTOR_STORE_DIR/chunks.json
- TF-IDF matrix rebuilt in-memory on load / after each mutation (fine for demo scale).
- Cosine similarity search with top-k + threshold filtering.
"""
import json
import re
import threading
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import VECTOR_STORE_DIR, TOP_K, RELEVANCE_THRESHOLD


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class VectorStore:
    def __init__(self, store_dir: Path = VECTOR_STORE_DIR):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_file = self.store_dir / "chunks.json"
        self._lock = threading.Lock()
        self.chunks: List[Dict[str, Any]] = []
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix = None
        self._load()

    # ---------- persistence ----------
    def _load(self):
        if self.chunks_file.exists():
            try:
                self.chunks = json.loads(self.chunks_file.read_text(encoding="utf-8"))
            except Exception:
                self.chunks = []
        self._rebuild_index()
        self._samples_ensured = bool(self.chunks)

    def ensure_samples(self):
        """Ingest bundled sample docs if the store is empty (first boot / fresh clone)."""
        if self._samples_ensured or self.chunks:
            return
        self._samples_ensured = True
        try:
            from app.config import SAMPLE_DOCS_DIR
            from app.services.ingestion import ingest_file
            sample_dir = Path(SAMPLE_DOCS_DIR)
            if sample_dir.exists():
                for path in sorted(sample_dir.iterdir()):
                    if path.is_file() and path.suffix.lower() in {".pdf", ".txt", ".md"}:
                        try:
                            self.chunks.extend(ingest_file(path))
                        except Exception as e:
                            print(f"[store] skip {path.name}: {e}")
                if self.chunks:
                    self._save()
                    self._rebuild_index()
        except Exception as e:
            print(f"[store] sample ingest failed: {e}")

    def _save(self):
        self.chunks_file.write_text(json.dumps(self.chunks, ensure_ascii=False, indent=1), encoding="utf-8")

    def _rebuild_index(self):
        if not self.chunks:
            self.vectorizer, self.matrix = None, None
            return
        corpus = [_normalize(c["text"]) for c in self.chunks]
        # char_wb + word n-grams handles short queries ("leave?") better than plain words
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), analyzer="word",
            min_df=1, stop_words="english", sublinear_tf=True,
        )
        try:
            self.matrix = self.vectorizer.fit_transform(corpus)
        except ValueError:
            # empty vocabulary (e.g. all stop-words) — fall back without stop words
            self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
            self.matrix = self.vectorizer.fit_transform(corpus)

    # ---------- mutations ----------
    def add_chunks(self, new_chunks: List[Dict[str, Any]]):
        with self._lock:
            self.chunks.extend(new_chunks)
            self._save()
            self._rebuild_index()

    def remove_document(self, filename: str) -> int:
        with self._lock:
            before = len(self.chunks)
            self.chunks = [c for c in self.chunks if c.get("source") != filename]
            removed = before - len(self.chunks)
            self._save()
            self._rebuild_index()
            return removed

    def clear(self):
        with self._lock:
            self.chunks = []
            self._save()
            self.vectorizer, self.matrix = None, None

    # ---------- search ----------
    def search(self, query: str, top_k: int = TOP_K) -> List[Dict[str, Any]]:
        """Return top-k chunks with cosine scores, sorted desc. No threshold applied here."""
        self.ensure_samples()
        with self._lock:
            if not self.chunks or self.vectorizer is None or self.matrix is None:
                return []
            q = _normalize(query)
            if not q:
                return []
            q_vec = self.vectorizer.transform([q])
            if q_vec.nnz == 0:
                return []  # no overlapping vocabulary at all
            sims = cosine_similarity(q_vec, self.matrix).flatten()
            idx = np.argsort(sims)[::-1][:top_k]
            results = []
            for i in idx:
                c = self.chunks[int(i)]
                results.append({
                    "text": c["text"],
                    "source": c.get("source", "unknown"),
                    "section": c.get("section", "N/A"),
                    "chunk_index": c.get("chunk_index", 0),
                    "score": float(sims[int(i)]),
                })
            return results

    @staticmethod
    def apply_filter(hits: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
        """Shared relevance rule: absolute threshold + low-confidence margin check.

        A weak top hit that barely beats the runner-up is likely a generic-term
        coincidence, so it only counts when decisive (>= 0.15) or clearly ahead
        (>= 1.6x the second-best score).
        """
        if not hits:
            return []
        best = hits[0]["score"]
        second = hits[1]["score"] if len(hits) > 1 else 0.0
        if best < threshold:
            return []
        if best < 0.15 and best < 1.6 * max(second, 1e-9):
            return []
        return [h for h in hits if h["score"] >= threshold]

    def search_filtered(self, query: str, top_k: int = TOP_K,
                        threshold: float = RELEVANCE_THRESHOLD) -> Tuple[List[Dict[str, Any]], float]:
        """Apply the shared relevance rule. Returns (passing_chunks, max_score)."""
        hits = self.search(query, top_k=top_k)
        if not hits:
            return [], 0.0
        return self.apply_filter(hits, threshold), hits[0]["score"]

    # ---------- stats ----------
    def stats(self) -> Dict[str, Any]:
        self.ensure_samples()
        docs: Dict[str, int] = {}
        for c in self.chunks:
            docs[c.get("source", "unknown")] = docs.get(c.get("source", "unknown"), 0) + 1
        return {"total_chunks": len(self.chunks), "documents": docs}


# singleton used by routers
store = VectorStore()
