import json
from pathlib import Path

import pytest

from knowledge_agent.db import connect, init_db
from knowledge_agent.import_service import ImportResult, import_pdf, import_pdf_folder
from knowledge_agent.job_service import run_folder_import_job
from knowledge_agent.models import BibliographyRecord, Document, Paper
from knowledge_agent.repositories import (
    ChunksRepository,
    DocumentsRepository,
    JobsRepository,
    PapersRepository,
)


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


def test_import_pdf_attaches_document_to_existing_metadata_doi(tmp_path: Path):
    source = tmp_path / "download.pdf"
    source.write_bytes(b"%PDF-1.4 downloaded with existing metadata")
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
        existing_paper = PapersRepository(conn).upsert_metadata(metadata)

        result = import_pdf(conn, library_root, source, metadata=metadata)
        document = DocumentsRepository(conn).find_by_paper_id(existing_paper.id)

    assert result.imported is True
    assert result.paper.id == existing_paper.id
    assert result.document.paper_id == existing_paper.id
    assert document is not None
    assert document.id == result.document.id
    assert (library_root / result.document.library_path).exists()


def test_import_pdf_moves_duplicate_hash_document_to_existing_metadata_paper(
    tmp_path: Path,
):
    source = tmp_path / "download.pdf"
    source.write_bytes(b"%PDF-1.4 duplicate bytes with later metadata")
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
        hash_match = import_pdf(conn, library_root, source)
        metadata_paper = PapersRepository(conn).upsert_metadata(metadata)

        result = import_pdf(conn, library_root, source, metadata=metadata)
        hash_document = DocumentsRepository(conn).find_by_hash(
            result.document.file_hash
        )
        papers = PapersRepository(conn).list_all()

    assert result.imported is False
    assert result.paper.id == metadata_paper.id
    assert result.document.id == hash_match.document.id
    assert result.document.paper_id == metadata_paper.id
    assert hash_document is not None
    assert hash_document.paper_id == metadata_paper.id
    assert [paper.id for paper in papers] == [metadata_paper.id]


def test_import_pdf_moves_duplicate_hash_chunks_to_existing_metadata_paper(
    tmp_path: Path,
    write_pdf,
):
    source = write_pdf(
        tmp_path / "download.pdf",
        ["The method uses retrieval grounded citations."],
    )
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
        hash_match = import_pdf(conn, library_root, source)
        metadata_paper = PapersRepository(conn).upsert_metadata(metadata)

        result = import_pdf(conn, library_root, source, metadata=metadata)
        chunks = ChunksRepository(conn)
        moved_chunks = chunks.list_for_paper(metadata_paper.id)
        old_chunks = chunks.list_for_paper(hash_match.paper.id)
        vector_count = chunks.vector_mapping_count_for_document(result.document.id)
        hits = chunks.search("retrieval grounded")

    assert result.paper.id == metadata_paper.id
    assert moved_chunks[0].paper_id == metadata_paper.id
    assert old_chunks == []
    assert vector_count == len(moved_chunks)
    assert hits[0].paper_id == metadata_paper.id
    assert hits[0].title == "Local Knowledge Agents"


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


def test_import_pdf_builds_vector_index_for_chunks(tmp_path: Path, write_pdf):
    source = write_pdf(
        tmp_path / "Vector Indexed Paper.pdf",
        [
            "The method uses retrieval augmented generation for source grounded answers.",
            "The evaluation measures contrastive retrieval quality on local papers.",
        ],
    )
    library_root = tmp_path / "library"
    vector_index_path = library_root / "indexes" / "vectors" / "chunks.json"

    with connect(library_root / "database.sqlite") as conn:
        init_db(conn)

        result = import_pdf(
            conn,
            library_root,
            source,
            vector_index_path=vector_index_path,
        )
        chunks = ChunksRepository(conn)
        stored_chunks = chunks.list_for_paper(result.paper.id)
        vector_count = chunks.vector_mapping_count_for_document(result.document.id)

    assert vector_index_path.exists()
    assert vector_count == len(stored_chunks)


def test_import_pdf_keeps_parse_success_when_vector_indexing_fails(
    tmp_path: Path,
    write_pdf,
    monkeypatch: pytest.MonkeyPatch,
):
    source = write_pdf(
        tmp_path / "Vector Failure Paper.pdf",
        ["The method uses retrieval augmented generation."],
    )
    library_root = tmp_path / "library"

    def fail_vector_indexing(self, document_id, entries):
        raise OSError("vector index unavailable")

    monkeypatch.setattr(
        "knowledge_agent.vector_index.LocalVectorIndex.replace_document_entries",
        fail_vector_indexing,
    )

    with connect(library_root / "database.sqlite") as conn:
        init_db(conn)

        result = import_pdf(conn, library_root, source)
        document = DocumentsRepository(conn).get(result.document.id)
        chunks = ChunksRepository(conn).list_for_paper(result.paper.id)

    assert document.parse_status == "parsed"
    assert document.parse_error is None
    assert len(chunks) == 1


def test_import_pdf_duplicate_retries_missing_vector_index(
    tmp_path: Path,
    write_pdf,
    monkeypatch: pytest.MonkeyPatch,
):
    source = write_pdf(
        tmp_path / "Retry Vector Paper.pdf",
        ["The method uses retrieval augmented generation."],
    )
    library_root = tmp_path / "library"
    original_replace = (
        __import__(
            "knowledge_agent.vector_index",
            fromlist=["LocalVectorIndex"],
        )
        .LocalVectorIndex
        .replace_document_entries
    )
    call_count = 0

    def fail_once(self, document_id, entries):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OSError("vector index unavailable")
        return original_replace(self, document_id, entries)

    monkeypatch.setattr(
        "knowledge_agent.vector_index.LocalVectorIndex.replace_document_entries",
        fail_once,
    )

    with connect(library_root / "database.sqlite") as conn:
        init_db(conn)

        first = import_pdf(conn, library_root, source)
        second = import_pdf(conn, library_root, source)
        chunks = ChunksRepository(conn)
        vector_count = chunks.vector_mapping_count_for_document(first.document.id)

    assert first.imported is True
    assert second.imported is False
    assert vector_count == 1


def test_import_pdf_folder_recursively_imports_pdfs_and_skips_duplicates(
    tmp_path: Path,
):
    folder = tmp_path / "folder"
    nested = folder / "nested"
    nested.mkdir(parents=True)
    first = folder / "First.pdf"
    duplicate = nested / "Duplicate.pdf"
    second = nested / "Second.pdf"
    first.write_bytes(b"%PDF-1.4 first")
    duplicate.write_bytes(b"%PDF-1.4 first")
    second.write_bytes(b"%PDF-1.4 second")
    (folder / "notes.txt").write_text("not a PDF", encoding="utf-8")
    library_root = tmp_path / "library"

    with connect(library_root / "database.sqlite") as conn:
        init_db(conn)
        result = import_pdf_folder(conn, library_root, folder)

    assert result.discovered_count == 3
    assert result.imported_count == 2
    assert result.skipped_count == 1
    assert result.failed_count == 0
    assert [item.paper.title for item in result.imports] == ["First", "Second"]


def test_import_pdf_folder_reports_per_file_failures(tmp_path: Path):
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "broken.pdf").mkdir()
    library_root = tmp_path / "library"

    with connect(library_root / "database.sqlite") as conn:
        init_db(conn)
        result = import_pdf_folder(conn, library_root, folder)

    assert result.discovered_count == 1
    assert result.imported_count == 0
    assert result.skipped_count == 0
    assert result.failed_count == 1
    assert result.failures[0].source_path.endswith("broken.pdf")


def test_folder_import_job_updates_progress(tmp_path: Path):
    folder = tmp_path / "folder"
    folder.mkdir()
    first = folder / "A First.pdf"
    duplicate = folder / "B Duplicate.pdf"
    broken = folder / "broken.pdf"
    first.write_bytes(b"%PDF-1.4 first")
    duplicate.write_bytes(b"%PDF-1.4 first")
    broken.mkdir()
    library_root = tmp_path / "library"

    with connect(library_root / "database.sqlite") as conn:
        init_db(conn)
        jobs = JobsRepository(conn)
        job = jobs.create(
            kind="folder_import",
            source_path=str(folder),
            description="Import folder",
        )

        completed = run_folder_import_job(conn, library_root, job.id, folder)
        result = json.loads(completed.result_json or "{}")
        papers = PapersRepository(conn).list_all()

    assert completed.status == "succeeded"
    assert completed.total_items == 3
    assert completed.processed_items == 3
    assert completed.succeeded_items == 2
    assert completed.failed_items == 1
    assert result["source_path"] == str(folder.resolve())
    assert result["discovered_count"] == 3
    assert result["imported_count"] == 1
    assert result["skipped_count"] == 1
    assert result["failed_count"] == 1
    assert result["failures"][0]["source_path"].endswith("broken.pdf")
    assert [paper.title for paper in papers] == ["A First"]


def test_folder_import_job_commits_progress_for_separate_readers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "A First.pdf").write_bytes(b"%PDF-1.4 first")
    (folder / "B Second.pdf").write_bytes(b"%PDF-1.4 second")
    library_root = tmp_path / "library"
    db_path = library_root / "database.sqlite"

    with connect(db_path) as conn:
        init_db(conn)
        job = JobsRepository(conn).create(
            kind="folder_import",
            source_path=str(folder),
            description="Import folder",
        )

    observed: dict[str, int | str] = {}
    import_calls = 0

    def fake_import_pdf(conn, library_root, source_path):
        nonlocal import_calls
        import_calls += 1
        call_number = import_calls
        if call_number == 2:
            with connect(db_path) as read_conn:
                mid_job = JobsRepository(read_conn).get(job.id)
            observed["status"] = mid_job.status
            observed["processed_items"] = mid_job.processed_items

        paper = Paper(
            id=call_number,
            title=source_path.stem,
            authors=None,
            year=None,
            doi=None,
            venue=None,
            abstract=None,
            citation_key=None,
            arxiv_id=None,
            entry_type=None,
            favorite=False,
            tags=[],
            created_at="now",
        )
        document = Document(
            id=call_number,
            paper_id=call_number,
            library_path=f"papers/{call_number}/paper.pdf",
            file_hash=f"hash-{call_number}",
            page_count=None,
            parse_status="failed",
            parse_error=None,
            created_at="now",
        )
        return ImportResult(paper=paper, document=document, imported=True)

    monkeypatch.setattr("knowledge_agent.job_service.import_pdf", fake_import_pdf)

    with connect(db_path) as conn:
        run_folder_import_job(conn, library_root, job.id, folder)

    assert observed == {"status": "running", "processed_items": 1}


def test_folder_import_job_result_json_uses_folder_import_response_shape(
    tmp_path: Path,
):
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "A First.pdf").write_bytes(b"%PDF-1.4 first")
    library_root = tmp_path / "library"

    with connect(library_root / "database.sqlite") as conn:
        init_db(conn)
        jobs = JobsRepository(conn)
        job = jobs.create(
            kind="folder_import",
            source_path=str(folder),
            description="Import folder",
        )

        completed = run_folder_import_job(conn, library_root, job.id, folder)
        result = json.loads(completed.result_json or "{}")

    assert result["imports"][0]["imported"] is True
    assert result["imports"][0]["paper"]["title"] == "A First"
    assert result["imports"][0]["document"]["library_path"].endswith("/paper.pdf")
    assert "paper_id" not in result["imports"][0]


def test_folder_import_job_records_failure(tmp_path: Path):
    source_path = tmp_path / "not-a-folder.pdf"
    source_path.write_bytes(b"%PDF-1.4 not folder")
    library_root = tmp_path / "library"

    with connect(library_root / "database.sqlite") as conn:
        init_db(conn)
        jobs = JobsRepository(conn)
        job = jobs.create(
            kind="folder_import",
            source_path=str(source_path),
            description="Import folder",
        )

        failed = run_folder_import_job(conn, library_root, job.id, source_path)

    assert failed.status == "failed"
    assert failed.error == "source path is not a folder"
    assert failed.processed_items == 0
