from pathlib import Path

from knowledge_agent.db import connect, init_db
from knowledge_agent.models import ChunkInput, ProviderSettings
from knowledge_agent.repositories import (
    ChunksRepository,
    DocumentsRepository,
    PapersRepository,
    QnaRepository,
    SettingsRepository,
)


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

    assert {
        "papers",
        "documents",
        "chunks",
        "chunks_fts",
        "settings",
        "qna_entries",
    }.issubset(table_names)


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


def test_provider_settings_default_and_roundtrip(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        settings = SettingsRepository(conn)

        default_settings = settings.get_provider_settings()
        saved_settings = settings.save_provider_settings(
            ProviderSettings(
                provider="openai_compatible",
                base_url="https://api.example.test/v1",
                model="research-model",
                api_key="secret-key",
                outbound_context_policy="snippets_only",
            )
        )
        reloaded_settings = settings.get_provider_settings()

    assert default_settings.provider == "none"
    assert default_settings.outbound_context_policy == "snippets_only"
    assert default_settings.to_public().api_key_configured is False
    assert saved_settings.to_public().api_key_configured is True
    assert saved_settings.to_public().api_key is None
    assert reloaded_settings.provider == "openai_compatible"
    assert reloaded_settings.base_url == "https://api.example.test/v1"
    assert reloaded_settings.model == "research-model"
    assert reloaded_settings.api_key == "secret-key"


def test_qna_entry_roundtrip(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        papers = PapersRepository(conn)
        qna = QnaRepository(conn)

        paper = papers.create(title="Grounded QA", year=2026, doi=None)
        entry = qna.create(
            paper_id=paper.id,
            question="What is the method?",
            answer="It uses retrieved snippets.",
            cited_chunks=[
                {
                    "chunk_id": 1,
                    "paper_id": paper.id,
                    "title": "Grounded QA",
                    "page_number": 2,
                    "snippet": "The method retrieves evidence.",
                    "source_span": "page:2:chars:0-30",
                }
            ],
            mode="strict",
            provider="openai_compatible",
        )
        entries = qna.list_for_paper(paper.id)

    assert entry.id == entries[0].id
    assert entries[0].question == "What is the method?"
    assert entries[0].answer == "It uses retrieved snippets."
    assert entries[0].cited_chunks[0]["page_number"] == 2
    assert entries[0].mode == "strict"
    assert entries[0].provider == "openai_compatible"


def test_relevant_chunks_for_paper_scores_current_paper_only(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        papers = PapersRepository(conn)
        documents = DocumentsRepository(conn)
        chunks = ChunksRepository(conn)

        current_paper = papers.create(title="Current Paper", year=2026, doi=None)
        other_paper = papers.create(title="Other Paper", year=2026, doi=None)
        current_document = documents.create(
            paper_id=current_paper.id,
            library_path="papers/current/paper.pdf",
            file_hash="current",
            page_count=2,
        )
        other_document = documents.create(
            paper_id=other_paper.id,
            library_path="papers/other/paper.pdf",
            file_hash="other",
            page_count=1,
        )
        chunks.replace_for_document(
            document_id=current_document.id,
            paper_id=current_paper.id,
            chunks=[
                ChunkInput(
                    page_number=1,
                    chunk_index=0,
                    text="The introduction discusses background motivation.",
                    source_span="page:1:chars:0-48",
                ),
                ChunkInput(
                    page_number=2,
                    chunk_index=0,
                    text="The method uses retrieval grounded citations.",
                    source_span="page:2:chars:0-45",
                ),
            ],
        )
        chunks.replace_for_document(
            document_id=other_document.id,
            paper_id=other_paper.id,
            chunks=[
                ChunkInput(
                    page_number=1,
                    chunk_index=0,
                    text="The other paper also mentions retrieval grounded citations.",
                    source_span="page:1:chars:0-58",
                )
            ],
        )

        relevant = chunks.relevant_for_paper(
            paper_id=current_paper.id,
            query="retrieval method citations",
            limit=1,
        )

    assert len(relevant) == 1
    assert relevant[0].paper_id == current_paper.id
    assert relevant[0].page_number == 2
    assert "method uses retrieval" in relevant[0].text
