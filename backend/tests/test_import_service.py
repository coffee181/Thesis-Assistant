from pathlib import Path

from knowledge_agent.db import connect, init_db
from knowledge_agent.import_service import import_pdf
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
