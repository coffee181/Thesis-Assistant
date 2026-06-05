from pathlib import Path

from knowledge_agent.db import connect, init_db
from knowledge_agent.repositories import DocumentsRepository, PapersRepository


def test_init_db_creates_tables(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        table_names = {
            row["name"]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table'"
            ).fetchall()
        }

    assert {"papers", "documents"}.issubset(table_names)


def test_paper_and_document_roundtrip(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        papers = PapersRepository(conn)
        documents = DocumentsRepository(conn)

        paper = papers.create(title="A Useful Paper", year=2024, doi="10.123/example")
        document = documents.create(
            paper_id=paper.id,
            library_path="papers/2024/a-useful-paper/paper.pdf",
            file_hash="abc123",
            page_count=None,
        )

        assert papers.list_all()[0].title == "A Useful Paper"
        assert documents.find_by_hash("abc123").id == document.id
