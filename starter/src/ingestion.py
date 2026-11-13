"""Read and normalize source data. TODO: implement functions."""
from pathlib import Path
from .models import DocumentPage
from pypdf import PdfReader
import unicodedata
import re


def section_for_page(page: int) -> str:
    """Map cut-PDF page number to a filterable section label."""
    if page <= 10:
        return "emphasis_verse"
    if page <= 19:
        return "voice"
    if page <= 27:
        return "gesture"
    return "selection"


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """TODO: extract each physical page; keep its page number and source.

    Detect and record pages with no text. OCR, when needed, is a separate step.
    """
    reader = PdfReader(path)
    pages = []
    for index, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        page_no = index + 1
        has_no_text = len(text.strip()) == 0
        pages.append(
            DocumentPage(
                document_id=document_id,
                source=source,
                page=page_no,
                text=text,
                metadata={
                    "has_no_text": has_no_text,
                    "section": section_for_page(page_no),
                    "page": page_no,
                },
            )
        )
    return pages


def normalize_text(text: str) -> str:
    """TODO: normalize Unicode and whitespace without discarding useful structure."""
    # Chuẩn hóa Unicode NFC và làm sạch khoảng trắng thừa nhưng giữ lại cấu trúc đoạn
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()
