import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from knowledge_agent.models import ChunkInput


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str


def extract_pdf_pages(pdf_path: Path) -> list[ExtractedPage]:
    reader = PdfReader(str(pdf_path))
    pages: list[ExtractedPage] = []
    for index, page in enumerate(reader.pages):
        text = _normalize_text(page.extract_text() or "")
        pages.append(ExtractedPage(page_number=index + 1, text=text))
    return pages


def chunk_pages(
    pages: list[ExtractedPage],
    max_chars: int = 1200,
    overlap: int = 120,
) -> list[ChunkInput]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be non-negative and smaller than max_chars")

    chunks: list[ChunkInput] = []
    for page in pages:
        text = _normalize_text(page.text)
        if not text:
            continue

        chunk_index = 0
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            chunk_text = text[start:end]
            chunks.append(
                ChunkInput(
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    text=chunk_text,
                    source_span=f"page:{page.page_number}:chars:{start}-{end}",
                )
            )
            if end == len(text):
                break
            start = end - overlap
            chunk_index += 1

    return chunks


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
