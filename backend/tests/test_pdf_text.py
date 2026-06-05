from pathlib import Path

from knowledge_agent.models import ChunkInput
from knowledge_agent.pdf_text import ExtractedPage, chunk_pages, extract_pdf_pages


def test_extract_pdf_pages_returns_page_numbered_text(tmp_path: Path, write_pdf):
    pdf_path = write_pdf(
        tmp_path / "paper.pdf",
        [
            "First page mentions retrieval augmented generation.",
            "Second page mentions contrastive search.",
        ],
    )

    pages = extract_pdf_pages(pdf_path)

    assert [page.page_number for page in pages] == [1, 2]
    assert "retrieval augmented generation" in pages[0].text
    assert "contrastive search" in pages[1].text


def test_chunk_pages_keeps_page_source_spans():
    pages = [
        ExtractedPage(
            page_number=3,
            text="abcdefghijklmnopqrstuvwxyz0123456789",
        )
    ]

    chunks = chunk_pages(pages, max_chars=10, overlap=2)

    assert chunks == [
        ChunkInput(
            page_number=3,
            chunk_index=0,
            text="abcdefghij",
            source_span="page:3:chars:0-10",
        ),
        ChunkInput(
            page_number=3,
            chunk_index=1,
            text="ijklmnopqr",
            source_span="page:3:chars:8-18",
        ),
        ChunkInput(
            page_number=3,
            chunk_index=2,
            text="qrstuvwxyz",
            source_span="page:3:chars:16-26",
        ),
        ChunkInput(
            page_number=3,
            chunk_index=3,
            text="yz01234567",
            source_span="page:3:chars:24-34",
        ),
        ChunkInput(
            page_number=3,
            chunk_index=4,
            text="6789",
            source_span="page:3:chars:32-36",
        ),
    ]


def test_chunk_pages_skips_empty_pages():
    pages = [ExtractedPage(page_number=1, text="   ")]

    assert chunk_pages(pages) == []
