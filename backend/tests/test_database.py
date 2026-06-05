from pathlib import Path

from knowledge_agent.db import connect, init_db
from knowledge_agent.models import ChunkInput
from knowledge_agent.repositories import ChunksRepository, DocumentsRepository, PapersRepository


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

    assert {"papers", "documents", "chunks", "chunks_fts"}.issubset(table_names)


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
        assert document.parse_status == "pending"


def test_chunks_replace_list_and_search(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        papers = PapersRepository(conn)
        documents = DocumentsRepository(conn)
        chunks = ChunksRepository(conn)

        paper = papers.create(title="Neural Retrieval Systems", year=2025, doi=None)
        document = documents.create(
            paper_id=paper.id,
            library_path="papers/2025/neural-retrieval-systems/paper.pdf",
            file_hash="hash-neural",
            page_count=None,
        )

        chunks.replace_for_document(
            document_id=document.id,
            paper_id=paper.id,
            chunks=[
                ChunkInput(
                    page_number=1,
                    chunk_index=0,
                    text="Retrieval augmented generation grounds answers in source passages.",
                    source_span="page:1:chars:0-64",
                ),
                ChunkInput(
                    page_number=2,
                    chunk_index=0,
                    text="Contrastive retrieval improves local literature search quality.",
                    source_span="page:2:chars:0-62",
                ),
            ],
        )

        stored_chunks = chunks.list_for_paper(paper.id)
        hits = chunks.search("contrastive retrieval")

    assert [chunk.page_number for chunk in stored_chunks] == [1, 2]
    assert stored_chunks[1].source_span == "page:2:chars:0-62"
    assert hits[0].paper_id == paper.id
    assert hits[0].title == "Neural Retrieval Systems"
    assert hits[0].page_number == 2
    assert "Contrastive retrieval" in hits[0].snippet
