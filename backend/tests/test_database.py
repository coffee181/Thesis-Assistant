from pathlib import Path

from knowledge_agent.db import connect, init_db
from knowledge_agent.models import (
    BibliographyRecord,
    ChunkInput,
    DiscoveryCandidate,
    ProviderSettings,
)
from knowledge_agent.repositories import (
    ChunksRepository,
    DocumentsRepository,
    HighlightsRepository,
    JobsRepository,
    NotesRepository,
    PapersRepository,
    QnaRepository,
    SearchResultsRepository,
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
        paper_columns = {
            row["name"]
            for row in conn.execute("pragma table_info(papers)").fetchall()
        }

    assert {
        "papers",
        "documents",
        "chunks",
        "chunks_fts",
        "settings",
        "qna_entries",
        "search_results",
        "notes",
        "highlights",
    }.issubset(table_names)
    assert {
        "authors",
        "venue",
        "abstract",
        "citation_key",
        "arxiv_id",
        "entry_type",
    }.issubset(paper_columns)


def test_paper_and_document_roundtrip(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        papers = PapersRepository(conn)
        documents = DocumentsRepository(conn)

        paper = papers.create(
            title="A Useful Paper",
            year=2024,
            doi="10.123/example",
            authors="Ada Lovelace and Grace Hopper",
            venue="Journal of Useful Systems",
            abstract="A concise abstract.",
            citation_key="lovelace2024useful",
            arxiv_id="2401.12345",
            entry_type="article",
        )
        document = documents.create(
            paper_id=paper.id,
            library_path="papers/2024/a-useful-paper/paper.pdf",
            file_hash="abc123",
            page_count=None,
        )

        assert papers.list_all()[0].title == "A Useful Paper"
        assert papers.list_all()[0].authors == "Ada Lovelace and Grace Hopper"
        assert papers.list_all()[0].venue == "Journal of Useful Systems"
        assert papers.list_all()[0].abstract == "A concise abstract."
        assert papers.list_all()[0].citation_key == "lovelace2024useful"
        assert papers.list_all()[0].arxiv_id == "2401.12345"
        assert papers.list_all()[0].entry_type == "article"
        assert documents.find_by_hash("abc123").id == document.id
    assert document.parse_status == "pending"


def test_jobs_repository_tracks_state_transitions(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        jobs = JobsRepository(conn)

        queued = jobs.create(
            kind="folder_import",
            source_path="F:\\papers",
            description="Import folder F:\\papers",
        )
        running = jobs.start(queued.id, total_items=3)
        progressed = jobs.update_progress(
            queued.id,
            processed_items=2,
            succeeded_items=1,
            failed_items=1,
            result_json='{"failures":[{"source_path":"broken.pdf","error":"bad pdf"}]}',
        )
        completed = jobs.complete(
            queued.id,
            processed_items=3,
            succeeded_items=2,
            failed_items=1,
            result_json='{"imported_count":2,"failed_count":1}',
        )
        failed = jobs.create(
            kind="folder_import",
            source_path="F:\\broken",
            description=None,
        )
        failed = jobs.fail(failed.id, "source path is not a folder")
        recent = jobs.list_recent()

    assert queued.status == "queued"
    assert queued.source_path == "F:\\papers"
    assert queued.description == "Import folder F:\\papers"
    assert running.status == "running"
    assert running.total_items == 3
    assert progressed.processed_items == 2
    assert progressed.succeeded_items == 1
    assert progressed.failed_items == 1
    assert completed.status == "succeeded"
    assert completed.processed_items == 3
    assert completed.result_json == '{"imported_count":2,"failed_count":1}'
    assert failed.status == "failed"
    assert failed.error == "source path is not a folder"
    assert [job.id for job in recent] == [failed.id, queued.id]


def test_upsert_metadata_updates_existing_doi(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        papers = PapersRepository(conn)
        first = papers.upsert_metadata(
            BibliographyRecord(
                citation_key="first2024",
                title="Original Title",
                authors="First Author",
                year=2024,
                doi="10.123/example",
                venue="Original Venue",
                abstract=None,
                arxiv_id=None,
                entry_type="article",
            )
        )
        second = papers.upsert_metadata(
            BibliographyRecord(
                citation_key="second2024",
                title="Updated Title",
                authors="Second Author",
                year=2025,
                doi="10.123/example",
                venue="Updated Venue",
                abstract="Updated abstract",
                arxiv_id="2501.00001",
                entry_type="inproceedings",
            )
        )
        all_papers = papers.list_all()

    assert first.id == second.id
    assert len(all_papers) == 1
    assert all_papers[0].title == "Updated Title"
    assert all_papers[0].authors == "Second Author"
    assert all_papers[0].year == 2025
    assert all_papers[0].venue == "Updated Venue"
    assert all_papers[0].abstract == "Updated abstract"
    assert all_papers[0].arxiv_id == "2501.00001"


def test_upsert_metadata_deduplicates_by_citation_key_without_doi(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        papers = PapersRepository(conn)
        first = papers.upsert_metadata(
            BibliographyRecord(
                citation_key="smith2024local",
                title="Local Search",
                authors="Smith",
                year=2024,
                doi=None,
                venue=None,
                abstract=None,
                arxiv_id=None,
                entry_type="article",
            )
        )
        second = papers.upsert_metadata(
            BibliographyRecord(
                citation_key="smith2024local",
                title="Local Search Revised",
                authors="Smith and Jones",
                year=2024,
                doi=None,
                venue="Library Systems",
                abstract=None,
                arxiv_id=None,
                entry_type="article",
            )
        )

    assert first.id == second.id
    assert second.title == "Local Search Revised"
    assert second.authors == "Smith and Jones"
    assert second.venue == "Library Systems"


def test_paper_favorite_roundtrip_and_filter(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        papers = PapersRepository(conn)
        first = papers.create(title="Favorite Paper", year=2026, doi=None)
        papers.create(title="Ordinary Paper", year=2026, doi=None)

        default_paper = papers.get(first.id)
        favorite_paper = papers.set_favorite(first.id, True)
        favorite_papers = papers.list_all(favorite=True)
        all_papers = papers.list_all()

    assert default_paper.favorite is False
    assert favorite_paper.favorite is True
    assert [paper.title for paper in favorite_papers] == ["Favorite Paper"]
    assert {paper.favorite for paper in all_papers} == {False, True}


def test_paper_tags_roundtrip_and_filter(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        papers = PapersRepository(conn)
        first = papers.create(title="Tagged Paper", year=2026, doi=None)
        papers.create(title="Other Paper", year=2026, doi=None)

        tagged = papers.add_tag(first.id, " reading ")
        tagged_again = papers.add_tag(first.id, "reading")
        tagged_papers = papers.list_all(tag="reading")
        untagged = papers.remove_tag(first.id, "reading")

    assert tagged.tags == ["reading"]
    assert tagged_again.tags == ["reading"]
    assert [paper.title for paper in tagged_papers] == ["Tagged Paper"]
    assert untagged.tags == []


def test_merge_papers_preserves_tags(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        papers = PapersRepository(conn)
        source = papers.create(title="Manual Paper", year=2026, doi=None)
        target = papers.create(title="Metadata Paper", year=2026, doi="10.123/example")
        papers.set_favorite(source.id, True)
        papers.add_tag(source.id, "manual")
        papers.add_tag(target.id, "reading")

        merged = papers.merge_papers(source.id, target.id)
        all_papers = papers.list_all()

    assert merged.favorite is True
    assert merged.tags == ["manual", "reading"]
    assert [paper.id for paper in all_papers] == [target.id]
    assert all_papers[0].tags == ["manual", "reading"]


def test_search_results_repository_replaces_query_results(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        repository = SearchResultsRepository(conn)
        first = repository.replace_for_query(
            "local rag",
            [
                DiscoveryCandidate(
                    source="openalex",
                    external_id="W123",
                    title="Local RAG",
                    authors="Jane Doe",
                    year=2024,
                    doi="10.123/local",
                    venue="Journal of Local Research",
                    abstract="Traceable assistants.",
                    arxiv_id=None,
                    pdf_url="https://example.test/local.pdf",
                    landing_url="https://example.test/local",
                )
            ],
        )
        second = repository.replace_for_query(
            "local rag",
            [
                DiscoveryCandidate(
                    source="arxiv",
                    external_id="2401.12345",
                    title="ArXiv Local RAG",
                    authors="Jane Doe and John Smith",
                    year=2024,
                    doi=None,
                    venue="arXiv",
                    abstract=None,
                    arxiv_id="2401.12345",
                    pdf_url="https://arxiv.org/pdf/2401.12345",
                    landing_url="https://arxiv.org/abs/2401.12345",
                )
            ],
        )

    assert [record.title for record in first] == ["Local RAG"]
    assert [record.title for record in second] == ["ArXiv Local RAG"]
    assert second[0].query == "local rag"
    assert second[0].pdf_url == "https://arxiv.org/pdf/2401.12345"


def test_search_results_repository_updates_duplicate_source_record(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        repository = SearchResultsRepository(conn)
        repository.replace_for_query(
            "first query",
            [
                DiscoveryCandidate(
                    source="openalex",
                    external_id="W123",
                    title="Original Title",
                    authors=None,
                    year=2024,
                    doi="10.123/local",
                    venue=None,
                    abstract=None,
                    arxiv_id=None,
                    pdf_url=None,
                    landing_url=None,
                )
            ],
        )
        updated = repository.replace_for_query(
            "second query",
            [
                DiscoveryCandidate(
                    source="openalex",
                    external_id="W123",
                    title="Updated Title",
                    authors="Jane Doe",
                    year=2025,
                    doi="10.123/local",
                    venue="Updated Venue",
                    abstract=None,
                    arxiv_id=None,
                    pdf_url="https://example.test/updated.pdf",
                    landing_url="https://example.test/updated",
                )
            ],
        )
        first_query_results = repository.list_for_query("first query")

    assert len(updated) == 1
    assert updated[0].title == "Updated Title"
    assert updated[0].authors == "Jane Doe"
    assert updated[0].venue == "Updated Venue"
    assert first_query_results == []


def test_notes_and_highlights_roundtrip(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        papers = PapersRepository(conn)
        notes = NotesRepository(conn)
        highlights = HighlightsRepository(conn)
        paper = papers.create(title="Readable Paper", year=2026, doi=None)
        other_paper = papers.create(title="Other Paper", year=2026, doi=None)

        note = notes.create(
            paper_id=paper.id,
            body="This answer is worth keeping.",
            page_number=2,
            source_span="page:2:selection",
            selected_text="retrieval augmented generation",
            note_type="assistant_answer",
            qna_id=None,
        )
        highlight = highlights.create(
            paper_id=paper.id,
            page_number=2,
            source_span="page:2:selection",
            selected_text="retrieval augmented generation",
            color="yellow",
            note_id=note.id,
        )
        highlights.create(
            paper_id=other_paper.id,
            page_number=1,
            source_span="page:1:selection",
            selected_text="other",
            color="yellow",
            note_id=None,
        )
        paper_notes = notes.list_for_paper(paper.id)
        paper_highlights = highlights.list_for_paper(paper.id)

    assert note.body == "This answer is worth keeping."
    assert paper_notes[0].selected_text == "retrieval augmented generation"
    assert paper_notes[0].note_type == "assistant_answer"
    assert highlight.note_id == note.id
    assert len(paper_highlights) == 1
    assert paper_highlights[0].page_number == 2


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
                proxy_url="http://127.0.0.1:7897",
            )
        )
        reloaded_settings = settings.get_provider_settings()

    assert default_settings.provider == "none"
    assert default_settings.outbound_context_policy == "snippets_only"
    assert default_settings.proxy_url is None
    assert default_settings.to_public().api_key_configured is False
    assert saved_settings.to_public().api_key_configured is True
    assert saved_settings.to_public().api_key is None
    assert saved_settings.proxy_url == "http://127.0.0.1:7897"
    assert reloaded_settings.provider == "openai_compatible"
    assert reloaded_settings.base_url == "https://api.example.test/v1"
    assert reloaded_settings.model == "research-model"
    assert reloaded_settings.api_key == "secret-key"
    assert reloaded_settings.proxy_url == "http://127.0.0.1:7897"


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
