"""Document parsing + chunking (ingestion pipeline).

Supports .pdf (pypdf), .txt, .md. Each chunk carries:
  { text, source, chunk_index, section }
Section detection: looks for headings like "Section 4.2", "§4.2", "# ...", "4.2 Title".
"""
import re
from pathlib import Path
from typing import List, Dict, Tuple

from app.config import CHUNK_SIZE_CHARS, CHUNK_OVERLAP_CHARS

SECTION_PATTERNS = [
    re.compile(r"(section\s+\d+(\.\d+)*)", re.IGNORECASE),
    re.compile(r"(§\s*\d+(\.\d+)*)"),
    re.compile(r"^#{1,4}\s+(.+)$", re.MULTILINE),
    re.compile(r"^(\d+(\.\d+)+\s+[A-Z][^\n]{2,80})$", re.MULTILINE),
]


def detect_sections(text: str) -> List[Tuple[int, str]]:
    """Return [(char_offset, label)] for detected section headings."""
    found: List[Tuple[int, str]] = []
    for pat in SECTION_PATTERNS:
        for m in pat.finditer(text):
            label = m.group(1).strip()
            # normalize "§4.2" -> "Section 4.2", keep short
            if label.startswith("§"):
                label = "Section " + label[1:].strip()
            found.append((m.start(), label[:80]))
    found.sort()
    return found


def section_for_offset(sections: List[Tuple[int, str]], offset: int) -> str:
    label = "N/A"
    for pos, name in sections:
        if pos <= offset:
            label = name
        else:
            break
    # shorten "Section 4.2 Leaves ..." -> "4.2"
    m = re.search(r"(\d+(\.\d+)+)", label)
    if m:
        return m.group(1)
    if label.lower().startswith("section"):
        return label[8:].strip()[:20] or label
    return label if label != "N/A" else "N/A"


def parse_document(filename: str, raw: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(raw))
        pages = [(p.extract_text() or "") for p in reader.pages]
        return "\n\n".join(pages).strip()
    elif ext in {".txt", ".md"}:
        return raw.decode("utf-8", errors="replace").strip()
    else:
        raise ValueError(f"Unsupported file type '{ext}'. Upload PDF, TXT, or MD.")


def recursive_split(text: str, chunk_size: int = CHUNK_SIZE_CHARS,
                    overlap: int = CHUNK_OVERLAP_CHARS) -> List[Tuple[str, int]]:
    """Split on paragraph -> sentence -> char boundaries. Returns [(chunk, char_offset)]."""
    text = re.sub(r"\r\n?", "\n", text).strip()
    if not text:
        return []
    separators = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]
    chunks: List[Tuple[str, int]] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        if end < n:
            # find best split point going backwards from `end`
            window = text[max(start, end - 400):end]
            cut = -1
            for sep in separators:
                idx = window.rfind(sep)
                if idx != -1:
                    cut = max(start, end - 400) + idx + len(sep)
                    break
            if cut > start + 200:
                end = cut
        chunk = text[start:end].strip()
        if chunk:
            chunks.append((chunk, start))
        if end >= n:
            break
        start = max(start + 1, end - overlap)
    return chunks


def _short_section(label: str) -> str:
    m = re.search(r"(\d+(\.\d+)+)", label)
    if m:
        return m.group(1)
    if label.lower().startswith("section"):
        return label[8:].strip()[:20] or label
    return label


def chunk_text(text: str, source: str) -> List[Dict]:
    """Split along section headings first (exact citations), then by size."""
    sections = detect_sections(text)
    segments: List[Tuple[str, str]] = []  # (segment_text, section_label)
    if not sections:
        segments.append((text, "N/A"))
    else:
        if sections[0][0] > 0:
            preamble = text[:sections[0][0]].strip()
            if preamble:
                segments.append((preamble, _short_section(sections[0][1])))
        for i, (pos, label) in enumerate(sections):
            end = sections[i + 1][0] if i + 1 < len(sections) else len(text)
            seg = text[pos:end].strip()
            if seg:
                segments.append((seg, _short_section(label)))
    out = []
    idx = 0
    for seg_text, label in segments:
        for chunk, _ in recursive_split(seg_text):
            out.append({
                "text": chunk,
                "source": source,
                "chunk_index": idx,
                "section": label,
            })
            idx += 1
    return out


def ingest_bytes(filename: str, raw: bytes) -> List[Dict]:
    text = parse_document(filename, raw)
    if not text.strip():
        raise ValueError(f"No extractable text found in '{filename}'.")
    chunks = chunk_text(text, source=filename)
    if not chunks:
        raise ValueError(f"Could not create chunks from '{filename}'.")
    return chunks


def ingest_file(path: Path) -> List[Dict]:
    return ingest_bytes(path.name, path.read_bytes())
