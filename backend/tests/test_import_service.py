from pathlib import Path

from knowledge_agent.db import connect, init_db
from knowledge_agent.import_service import import_pdf
from knowledge_agent.models import BibliographyRecord
from knowledge_agent.repositories import ChunksRepository, DocumentsRepository


def test_import_pdf_copies_file_and_creates_records(tmp_path: Path):
    source = tmp_path / "Source Paper.pdf"
    source.write_bytes(b"%PDF-1.4 fake pdf")
    library_root = tmp_path / "library"

    with connect(library_root / "database.sqlite") as conn:
        init_db(conn)

        result = import_pdf(conn, library_root, source)

    copied_file = library_root / result.document.library_path
    assert result.imported is True
    assert result.paper.title == "Source Paper"
    assert copied_file.exists()
    assert copied_file.read_bytes() == b"%PDF-1.4 fake pdf"


def test_import_pdf_deduplicates_by_hash(tmp_path: Path):
    source = tmp_path / "Duplicate.pdf"
    source.write_bytes(b"%PDF-1.4 same bytes")
    library_root = tmp_path / "library"

    with connect(library_root / "database.sqlite") as conn:
        init_db(conn)

        first = import_pdf(conn, library_root, source)
        second = import_pdf(conn, library_root, source)

    assert first.imported is True
    assert second.imported is False
    assert first.document.id == second.document.id
    assert first.paper.id == second.paper.id


def test_import_pdf_uses_metadata_when_provided(tmp_path: Path):
    source = tmp_path / "download.pdf"
    source.write_bytes(b"%PDF-1.4 downloaded")
    library_root = tmp_path / "library"
    metadata = BibliographyRecord(
        citation_key="doe2024local",
        title="Local Knowledge Agents",
        authors="Jane Doe and John Smith",
        year=2024,
        doi="10.1234/local",
        venue="Journal of Local Research",
        abstract="Traceable local assistants.",
        arxiv_id="2401.12345",
        entry_type="article",
    )

    with connect(library_root / "database.sqlite") as conn:
        init_db(conn)

        result = import_pdf(conn, library_root, source, metadata=metadata)

    assert result.imported is True
    assert result.paper.title == "Local Knowledge Agents"
    assert result.paper.authors == "Jane Doe and John Smith"
    assert result.paper.year == 2024
    assert result.paper.doi == "10.1234/local"
    assert result.paper.venue == "Journal of Local Research"
    assert result.paper.citation_key == "doe2024local"
    assert result.paper.arxiv_id == "2401.12345"


def test_import_pdf_duplicate_hash_updates_existing_metadata(tmp_path: Path):
    source = tmp_path / "duplicate-download.pdf"
    source.write_bytes(b"%PDF-1.4 duplicate downloaded")
    library_root = tmp_path / "library"
    metadata = BibliographyRecord(
        citation_key="doe2024local",
        title="Local Knowledge Agents",
        authors="Jane Doe",
        year=2024,
        doi="10.1234/local",
        venue="Journal of Local Research",
        abstract=None,
        arxiv_id=None,
        entry_type="article",
    )

    with connect(library_root / "database.sqlite") as conn:
        init_db(conn)

        first = import_pdf(conn, library_root, source)
        second = import_pdf(conn, library_root, source, metadata=metadata)

    assert second.imported is False
    assert second.document.id == first.document.id
    assert second.paper.id == first.paper.id
    assert second.paper.title == "Local Knowledge Agents"
    assert second.paper.doi == "10.1234/local"
    assert second.paper.authors == "Jane Doe"


def test_import_pdf_extracts_text_chunks_for_valid_pdf(tmp_path: Path, write_pdf):
    source = write_pdf(
        tmp_path / "Extractable Paper.pdf",
        [
            "The method uses retrieval augmented generation for source grounded answers.",
            "The evaluation measures contrastive retrieval quality on local papers.",
        ],
    )
    library_root = tmp_path / "library"

    with connect(library_root / "database.sqlite") as conn:
        init_db(conn)

        result = import_pdf(conn, library_root, source)
        document = DocumentsRepository(conn).get(result.document.id)
        chunks = ChunksRepository(conn)
        stored_chunks = chunks.list_for_paper(result.paper.id)
        hits = chunks.search("contrastive retrieval")

    assert document.page_count == 2
    assert document.parse_status == "parsed"
    assert document.parse_error is None
    assert [chunk.page_number for chunk in stored_chunks] == [1, 2]
    assert "source grounded answers" in stored_chunks[0].text
    assert hits[0].paper_id == result.paper.id
    assert hits[0].page_number == 2
