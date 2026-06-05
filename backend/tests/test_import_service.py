from pathlib import Path

from knowledge_agent.db import connect, init_db
from knowledge_agent.import_service import import_pdf


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
