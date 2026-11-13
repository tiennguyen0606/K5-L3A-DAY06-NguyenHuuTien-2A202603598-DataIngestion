"""Read and normalize source data. TODO: implement functions."""
from pathlib import Path
from .models import DocumentPage
from pypdf import PdfReader
import unicodedata
import re

_HEADER_LINE = re.compile(
    r"^(?:"
    r"ECLECTIC SERIES\.?"
    r"|SIXTH\s*RE\s*ADER\.?"
    r"|SIXTH READER\.?"
    r"|MCGUFFEY'?S"
    r"|MCGUFFEY'S\s+SIXTH READER\.?"
    r")\s*$",
    re.IGNORECASE,
)
_PAGE_NUM_LINE = re.compile(r"^\(?\d{1,3}\)?$")
_RUNNING_PAGE = re.compile(r"^\d{1,3}\s+ECLECTIC SERIES\.?$", re.IGNORECASE)
_SOFT_HYPHEN = re.compile(r"-\s*\n\s*")


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
    """Normalize Unicode, drop running headers/page crumbs, keep paragraph breaks."""
    text = unicodedata.normalize("NFC", text)
    text = _SOFT_HYPHEN.sub("", text)
    kept: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            kept.append("")
            continue
        if _HEADER_LINE.match(line) or _PAGE_NUM_LINE.match(line) or _RUNNING_PAGE.match(line):
            continue
        # "36 ECLECTIC SERIES." / "SIXTH READER. 37" style crumbs
        line = re.sub(r"^\d{1,3}\s+ECLECTIC SERIES\.?\s*", "", line, flags=re.I)
        line = re.sub(r"^SIXTH\s*RE\s*ADER\.\s*\d{1,3}\s*", "", line, flags=re.I)
        line = re.sub(r"^SIXTH READER\.\s*\d{1,3}\s*", "", line, flags=re.I)
        if line:
            kept.append(line)
    text = "\n".join(kept)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()
