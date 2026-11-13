"""Implement fixed-size and structure-aware chunking."""
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """TODO: split text into overlapping windows and retain page metadata."""
    text = page.text
    chunks = []
    start = 0
    text_len = len(text)

    if text_len == 0:
        return []

    chunk_idx = 0
    while start < text_len:
        end = min(start + size, text_len)
        chunk_text = text[start:end]
        chunk_id = f"{page.document_id}_p{page.page}_fixed_{chunk_idx}"

        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=chunk_text,
                metadata=page.metadata.copy()
            )
        )
        if end == text_len:
            break
        start += size - overlap
        chunk_idx += 1
    return chunks

def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """TODO: group paragraphs, split oversized paragraphs and retain metadata."""
    paragraphs = page.text.split("\n\n")
    chunks = []
    chunk_idx = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # Nếu đoạn văn quá dài vượt quá max_size, cắt nhỏ nó theo ký tự
        if len(para) > max_size:
            sub_start = 0
            while sub_start < len(para):
                sub_end = min(sub_start + max_size, len(para))
                sub_text = para[sub_start:sub_end]
                chunks.append(
                    Chunk(
                        chunk_id=f"{page.document_id}_p{page.page}_para_{chunk_idx}",
                        document_id=page.document_id,
                        source=page.source,
                        page=page.page,
                        text=sub_text,
                        metadata=page.metadata.copy()
                    )
                )
                chunk_idx += 1
                sub_start += max_size
        else:
            chunks.append(
                Chunk(
                    chunk_id=f"{page.document_id}_p{page.page}_para_{chunk_idx}",
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=para,
                    metadata=page.metadata.copy()
                )
            )
            chunk_idx += 1
    return chunks