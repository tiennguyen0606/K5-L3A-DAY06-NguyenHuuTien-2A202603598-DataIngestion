"""Implement fixed-size and structure-aware chunking."""
import re
from .models import Chunk, DocumentPage

_SENT_END = re.compile(r"[.!?][\"')\]]?\s+")


def _snap_end(text: str, start: int, ideal_end: int) -> int:
    """Prefer ending near a sentence boundary in the last ~40% of the window."""
    if ideal_end >= len(text):
        return len(text)
    window = text[start:ideal_end]
    if len(window) < 40:
        return ideal_end
    search_from = int(len(window) * 0.6)
    best = -1
    for m in _SENT_END.finditer(window):
        if m.end() >= search_from:
            best = m.end()
    if best > 0:
        return start + best
    # fallback: paragraph break
    para = window.rfind("\n\n", search_from)
    if para > 0:
        return start + para + 2
    return ideal_end


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Split into overlapping windows; snap cuts to sentence ends when possible."""
    text = page.text
    if not text:
        return []

    chunks: list[Chunk] = []
    start = 0
    chunk_idx = 0
    text_len = len(text)
    while start < text_len:
        ideal_end = min(start + size, text_len)
        end = _snap_end(text, start, ideal_end)
        if end <= start:
            end = ideal_end
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(
                Chunk(
                    chunk_id=f"{page.document_id}_p{page.page}_fixed_{chunk_idx}",
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=chunk_text,
                    metadata={**page.metadata.copy(), "chunking": "fixed_sentence"},
                )
            )
            chunk_idx += 1
        if end >= text_len:
            break
        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Group paragraphs; oversized paragraphs use sentence-aware windows."""
    paragraphs = page.text.split("\n\n")
    chunks: list[Chunk] = []
    chunk_idx = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_size:
            chunks.append(
                Chunk(
                    chunk_id=f"{page.document_id}_p{page.page}_para_{chunk_idx}",
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=para,
                    metadata={**page.metadata.copy(), "chunking": "paragraph"},
                )
            )
            chunk_idx += 1
            continue

        # oversized: reuse fixed_size logic on a synthetic page fragment
        frag = DocumentPage(
            document_id=page.document_id,
            source=page.source,
            page=page.page,
            text=para,
            metadata=page.metadata,
        )
        overlap = max(50, max_size // 10)
        for sub in fixed_size(frag, size=max_size, overlap=overlap):
            sub.chunk_id = f"{page.document_id}_p{page.page}_para_{chunk_idx}"
            sub.metadata = {**page.metadata.copy(), "chunking": "paragraph_sentence"}
            chunks.append(sub)
            chunk_idx += 1
    return chunks
