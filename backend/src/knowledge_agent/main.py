from pathlib import Path
import sqlite3
from typing import Callable

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse
import httpx

from knowledge_agent.assistant import (
    ProviderConfigurationError,
    answer_current_paper_question,
    answer_selected_text,
)
from knowledge_agent.bibliography import (
    export_bibtex,
    export_ris,
    parse_bibliography,
)
from knowledge_agent.config import AppConfig, load_config
from knowledge_agent.db import connect, init_db
from knowledge_agent.discovery import ExternalDiscoveryClient
from knowledge_agent.import_service import import_pdf, import_pdf_folder
from knowledge_agent.models import BibliographyRecord, Chunk, ProviderSettings, SearchResultRecord
from knowledge_agent.providers import ChatProvider, HttpChatProvider
from knowledge_agent.repositories import (
    ChunksRepository,
    DocumentsRepository,
    HighlightsRepository,
    NotesRepository,
    PapersRepository,
    SettingsRepository,
    SearchResultsRepository,
)
from knowledge_agent.schemas import (
    AskPaperQuestionRequest,
    AskPaperQuestionResponse,
    CitationResponse,
    CreateHighlightRequest,
    CreateNoteRequest,
    ExternalSearchResponse,
    ExportBibliographyResponse,
    HighlightResponse,
    HighlightsResponse,
    ImportFolderFailureResponse,
    ImportFolderRequest,
    ImportFolderResponse,
    ImportPendingDownloadRequest,
    ImportBibliographyRequest,
    ImportBibliographyResponse,
    ImportPdfRequest,
    ImportPdfResponse,
    LibraryResponse,
    LocalSearchResponse,
    NoteResponse,
    NotesResponse,
    OpenPdfDownloadRequest,
    OpenPdfDownloadResponse,
    PapersResponse,
    ProviderSettingsRequest,
    ProviderSettingsResponse,
    ReaderContextResponse,
    ReaderPageResponse,
    SelectLibraryRequest,
    SelectedTextAssistantRequest,
)


def create_app(
    library_dir: Path | None = None,
    chat_provider: ChatProvider | None = None,
    discovery_client: ExternalDiscoveryClient | None = None,
    pdf_downloader: Callable[[str, Path], None] | None = None,
) -> FastAPI:
    config = load_config(library_dir)
    config.library_dir.mkdir(parents=True, exist_ok=True)
    resolved_chat_provider = chat_provider or HttpChatProvider()
    resolved_discovery_client = discovery_client or ExternalDiscoveryClient()
    resolved_pdf_downloader = pdf_downloader or _download_pdf

    with connect(config.database_path) as conn:
        init_db(conn)

    app = FastAPI(title="Knowledge Agent Backend")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "knowledge-agent-backend"}

    @app.get("/api/library", response_model=LibraryResponse)
    def get_library() -> LibraryResponse:
        return _library_response(config)

    @app.put("/api/library", response_model=LibraryResponse)
    def select_library(request: SelectLibraryRequest) -> LibraryResponse:
        nonlocal config
        selected = load_config(Path(request.library_dir))
        try:
            selected.library_dir.mkdir(parents=True, exist_ok=True)
            with connect(selected.database_path) as conn:
                init_db(conn)
        except (OSError, sqlite3.Error) as exc:
            raise HTTPException(
                status_code=400,
                detail="could not select library",
            ) from exc
        config = selected
        return _library_response(config)

    @app.get("/api/papers", response_model=PapersResponse)
    def list_papers() -> PapersResponse:
        with connect(config.database_path) as conn:
            papers = PapersRepository(conn).list_all()
        return PapersResponse(papers=papers)

    @app.get(
        "/api/settings/provider",
        response_model=ProviderSettingsResponse,
    )
    def get_provider_settings() -> ProviderSettingsResponse:
        with connect(config.database_path) as conn:
            settings = SettingsRepository(conn).get_provider_settings()
        return ProviderSettingsResponse.model_validate(settings.to_public())

    @app.put(
        "/api/settings/provider",
        response_model=ProviderSettingsResponse,
    )
    def save_provider_settings(
        request: ProviderSettingsRequest,
    ) -> ProviderSettingsResponse:
        settings = ProviderSettings(
            provider=request.provider,
            base_url=_blank_to_none(request.base_url),
            model=_blank_to_none(request.model),
            api_key=_blank_to_none(request.api_key),
            outbound_context_policy=request.outbound_context_policy,
        )
        with connect(config.database_path) as conn:
            saved_settings = SettingsRepository(conn).save_provider_settings(settings)
        return ProviderSettingsResponse.model_validate(saved_settings.to_public())

    @app.get("/api/search/local", response_model=LocalSearchResponse)
    def search_local(q: str = Query(min_length=1)) -> LocalSearchResponse:
        query = q.strip()
        with connect(config.database_path) as conn:
            hits = ChunksRepository(conn).search(query)
        return LocalSearchResponse(query=query, hits=hits)

    @app.get("/api/search/external", response_model=ExternalSearchResponse)
    def search_external(q: str = Query(min_length=1)) -> ExternalSearchResponse:
        query = q.strip()
        candidates = resolved_discovery_client.search(query)
        with connect(config.database_path) as conn:
            results = SearchResultsRepository(conn).replace_for_query(
                query,
                candidates,
            )
        return ExternalSearchResponse(query=query, results=results)

    @app.get(
        "/api/papers/{paper_id}/reader-context",
        response_model=ReaderContextResponse,
    )
    def get_reader_context(paper_id: int) -> ReaderContextResponse:
        with connect(config.database_path) as conn:
            papers = PapersRepository(conn)
            documents = DocumentsRepository(conn)
            chunks = ChunksRepository(conn)
            try:
                paper = papers.get(paper_id)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail="paper not found") from exc

            document = documents.find_by_paper_id(paper_id)
            if document is None:
                raise HTTPException(status_code=404, detail="document not found")

            paper_chunks = chunks.list_for_paper(paper_id)

        return ReaderContextResponse(
            paper=paper,
            document=document,
            pages=_reader_pages_from_chunks(paper_chunks),
        )

    @app.get("/api/papers/{paper_id}/pdf")
    def get_paper_pdf(paper_id: int) -> FileResponse:
        active_config = config
        with connect(active_config.database_path) as conn:
            papers = PapersRepository(conn)
            documents = DocumentsRepository(conn)
            try:
                paper = papers.get(paper_id)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail="paper not found") from exc

            document = documents.find_by_paper_id(paper_id)
            if document is None:
                raise HTTPException(status_code=404, detail="document not found")

        pdf_path = _managed_document_path(
            active_config.library_dir,
            document.library_path,
        )
        if pdf_path is None or not pdf_path.exists() or not pdf_path.is_file():
            raise HTTPException(status_code=404, detail="PDF file not found")

        filename = f"{_slugify(paper.title) or 'paper'}.pdf"
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=filename,
            content_disposition_type="inline",
        )

    @app.post(
        "/api/papers/{paper_id}/assistant/ask",
        response_model=AskPaperQuestionResponse,
    )
    def ask_current_paper(
        paper_id: int,
        request: AskPaperQuestionRequest,
    ) -> AskPaperQuestionResponse:
        try:
            with connect(config.database_path) as conn:
                answer = answer_current_paper_question(
                    conn=conn,
                    paper_id=paper_id,
                    question=request.question,
                    chat_provider=resolved_chat_provider,
                )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="paper not found") from exc
        except ProviderConfigurationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return AskPaperQuestionResponse(
            answer=answer.answer,
            citations=[
                CitationResponse(**citation.to_dict())
                for citation in answer.citations
            ],
            mode=answer.mode,
            provider=answer.provider,
            qna_id=answer.qna_id,
        )

    @app.post(
        "/api/papers/{paper_id}/assistant/selection",
        response_model=AskPaperQuestionResponse,
    )
    def ask_selected_text(
        paper_id: int,
        request: SelectedTextAssistantRequest,
    ) -> AskPaperQuestionResponse:
        try:
            with connect(config.database_path) as conn:
                answer = answer_selected_text(
                    conn=conn,
                    paper_id=paper_id,
                    selected_text=request.selected_text,
                    page_number=request.page_number,
                    source_span=request.source_span,
                    action=request.action,
                    instruction=request.instruction,
                    chat_provider=resolved_chat_provider,
                )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="paper not found") from exc
        except ProviderConfigurationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return AskPaperQuestionResponse(
            answer=answer.answer,
            citations=[
                CitationResponse(**citation.to_dict())
                for citation in answer.citations
            ],
            mode=answer.mode,
            provider=answer.provider,
            qna_id=answer.qna_id,
        )

    @app.post(
        "/api/notes",
        response_model=NoteResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_note(request: CreateNoteRequest) -> NoteResponse:
        try:
            with connect(config.database_path) as conn:
                PapersRepository(conn).get(request.paper_id)
                note = NotesRepository(conn).create(
                    paper_id=request.paper_id,
                    body=request.body,
                    page_number=request.page_number,
                    source_span=request.source_span,
                    selected_text=request.selected_text,
                    note_type=request.note_type,
                    qna_id=request.qna_id,
                )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="paper not found") from exc
        return NoteResponse.model_validate(note)

    @app.get(
        "/api/papers/{paper_id}/notes",
        response_model=NotesResponse,
    )
    def list_notes(paper_id: int) -> NotesResponse:
        try:
            with connect(config.database_path) as conn:
                PapersRepository(conn).get(paper_id)
                notes = NotesRepository(conn).list_for_paper(paper_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="paper not found") from exc
        return NotesResponse(notes=notes)

    @app.post(
        "/api/highlights",
        response_model=HighlightResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_highlight(request: CreateHighlightRequest) -> HighlightResponse:
        try:
            with connect(config.database_path) as conn:
                PapersRepository(conn).get(request.paper_id)
                highlight = HighlightsRepository(conn).create(
                    paper_id=request.paper_id,
                    page_number=request.page_number,
                    source_span=request.source_span,
                    selected_text=request.selected_text,
                    color=request.color,
                    note_id=request.note_id,
                )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="paper not found") from exc
        return HighlightResponse.model_validate(highlight)

    @app.get(
        "/api/papers/{paper_id}/highlights",
        response_model=HighlightsResponse,
    )
    def list_highlights(paper_id: int) -> HighlightsResponse:
        try:
            with connect(config.database_path) as conn:
                PapersRepository(conn).get(paper_id)
                highlights = HighlightsRepository(conn).list_for_paper(paper_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="paper not found") from exc
        return HighlightsResponse(highlights=highlights)

    @app.post(
        "/api/imports/pdf",
        response_model=ImportPdfResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def import_pdf_endpoint(request: ImportPdfRequest) -> ImportPdfResponse:
        active_config = config
        source_path = Path(request.source_path)
        if not source_path.exists():
            raise HTTPException(status_code=404, detail="source PDF not found")
        try:
            with connect(active_config.database_path) as conn:
                result = import_pdf(conn, active_config.library_dir, source_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ImportPdfResponse(
            imported=result.imported,
            paper=result.paper,
            document=result.document,
        )

    @app.post(
        "/api/imports/folder",
        response_model=ImportFolderResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def import_folder_endpoint(request: ImportFolderRequest) -> ImportFolderResponse:
        active_config = config
        source_dir = Path(request.source_dir)
        if not source_dir.exists():
            raise HTTPException(status_code=404, detail="source folder not found")
        try:
            with connect(active_config.database_path) as conn:
                result = import_pdf_folder(conn, active_config.library_dir, source_dir)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ImportFolderResponse(
            source_path=result.source_path,
            discovered_count=result.discovered_count,
            imported_count=result.imported_count,
            skipped_count=result.skipped_count,
            failed_count=result.failed_count,
            imports=[
                ImportPdfResponse(
                    imported=item.imported,
                    paper=item.paper,
                    document=item.document,
                )
                for item in result.imports
            ],
            failures=[
                ImportFolderFailureResponse(
                    source_path=failure.source_path,
                    error=failure.error,
                )
                for failure in result.failures
            ],
        )

    @app.post(
        "/api/imports/bibliography",
        response_model=ImportBibliographyResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def import_bibliography_endpoint(
        request: ImportBibliographyRequest,
    ) -> ImportBibliographyResponse:
        source_path = Path(request.source_path)
        if not source_path.exists():
            raise HTTPException(status_code=404, detail="source bibliography not found")
        try:
            format_name = _bibliography_format(request.format, source_path)
            records = parse_bibliography(
                source_path.read_text(encoding="utf-8"),
                format_name,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        imported_count = 0
        updated_count = 0
        imported_papers = []
        with connect(config.database_path) as conn:
            papers = PapersRepository(conn)
            known_ids = {paper.id for paper in papers.list_all()}
            for record in records:
                paper = papers.upsert_metadata(record)
                imported_papers.append(paper)
                if paper.id in known_ids:
                    updated_count += 1
                else:
                    imported_count += 1
                    known_ids.add(paper.id)

        return ImportBibliographyResponse(
            format=format_name,
            imported_count=imported_count,
            updated_count=updated_count,
            papers=imported_papers,
        )

    @app.get(
        "/api/exports/bibliography",
        response_model=ExportBibliographyResponse,
    )
    def export_bibliography_endpoint(
        format: str = Query(pattern="^(bib|bibtex|ris)$"),
    ) -> ExportBibliographyResponse:
        format_name = _bibliography_format(format, None)
        with connect(config.database_path) as conn:
            papers = PapersRepository(conn).list_all()
        content = export_bibtex(papers) if format_name == "bibtex" else export_ris(papers)
        return ExportBibliographyResponse(format=format_name, content=content)

    @app.post(
        "/api/downloads/open-pdf",
        response_model=OpenPdfDownloadResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def download_open_pdf(
        request: OpenPdfDownloadRequest,
    ) -> OpenPdfDownloadResponse:
        active_config = config
        with connect(active_config.database_path) as conn:
            try:
                result = SearchResultsRepository(conn).get(request.search_result_id)
            except KeyError as exc:
                raise HTTPException(
                    status_code=404,
                    detail="search result not found",
                ) from exc

        if not result.pdf_url:
            raise HTTPException(
                status_code=400,
                detail="search result has no open PDF URL",
            )

        pending_path = _pending_download_path(active_config.library_dir, result)
        pending_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            resolved_pdf_downloader(result.pdf_url, pending_path)
        except Exception as exc:
            raise HTTPException(status_code=502, detail="PDF download failed") from exc
        return OpenPdfDownloadResponse(
            pending_path=str(pending_path),
            result=result,
        )

    @app.post(
        "/api/imports/pending-download",
        response_model=ImportPdfResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def import_pending_download(
        request: ImportPendingDownloadRequest,
    ) -> ImportPdfResponse:
        active_config = config
        pending_path = Path(request.pending_path).resolve()
        pending_root = (active_config.library_dir / "downloads" / "pending").resolve()
        if not pending_path.exists():
            raise HTTPException(status_code=404, detail="pending PDF not found")
        if pending_path != pending_root and pending_root not in pending_path.parents:
            raise HTTPException(
                status_code=400,
                detail="pending PDF path outside library",
            )

        try:
            with connect(active_config.database_path) as conn:
                search_result = SearchResultsRepository(conn).get(
                    request.search_result_id
                )
                result = import_pdf(
                    conn=conn,
                    library_root=active_config.library_dir,
                    source_path=pending_path,
                    metadata=_metadata_from_search_result(search_result),
                )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="search result not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return ImportPdfResponse(
            imported=result.imported,
            paper=result.paper,
            document=result.document,
        )

    return app


def _library_response(config: AppConfig) -> LibraryResponse:
    with connect(config.database_path) as conn:
        paper_count = len(PapersRepository(conn).list_all())
    return LibraryResponse(
        library_dir=str(config.library_dir),
        database_path=str(config.database_path),
        paper_count=paper_count,
    )


def _managed_document_path(library_dir: Path, library_path: str) -> Path | None:
    library_root = library_dir.resolve()
    candidate = (library_root / library_path).resolve()
    if candidate == library_root or library_root not in candidate.parents:
        return None
    return candidate


def _reader_pages_from_chunks(chunks: list[Chunk]) -> list[ReaderPageResponse]:
    page_texts: dict[int, str] = {}
    for chunk in chunks:
        current = page_texts.get(chunk.page_number, "")
        page_texts[chunk.page_number] = _append_with_overlap(current, chunk.text)

    return [
        ReaderPageResponse(page_number=page_number, text=text)
        for page_number, text in sorted(page_texts.items())
    ]


def _append_with_overlap(current: str, next_text: str) -> str:
    if not current:
        return next_text

    max_overlap = min(len(current), len(next_text))
    for overlap in range(max_overlap, 0, -1):
        if current.endswith(next_text[:overlap]):
            return current + next_text[overlap:]
    return current + next_text


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _download_pdf(url: str, target_path: Path) -> None:
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        target_path.write_bytes(response.content)


def _pending_download_path(
    library_dir: Path,
    result: SearchResultRecord,
) -> Path:
    slug = _slugify(result.title) or "paper"
    return library_dir / "downloads" / "pending" / f"{result.id}-{slug}.pdf"


def _metadata_from_search_result(result: SearchResultRecord) -> BibliographyRecord:
    return BibliographyRecord(
        citation_key=None,
        title=result.title,
        authors=result.authors,
        year=result.year,
        doi=result.doi,
        venue=result.venue,
        abstract=result.abstract,
        arxiv_id=result.arxiv_id,
        entry_type="article",
    )


def _bibliography_format(format_name: str | None, source_path: Path | None) -> str:
    normalized = (format_name or "auto").strip().lower()
    if normalized == "auto":
        if source_path is None:
            raise ValueError("bibliography format is required")
        suffix = source_path.suffix.lower()
        if suffix == ".bib":
            return "bibtex"
        if suffix == ".ris":
            return "ris"
        raise ValueError("unsupported bibliography format")
    if normalized == "bib":
        return "bibtex"
    if normalized in {"bibtex", "ris"}:
        return normalized
    raise ValueError("unsupported bibliography format")


def _slugify(value: str) -> str:
    lowered = value.lower()
    normalized = "".join(char if char.isalnum() else "-" for char in lowered)
    return "-".join(part for part in normalized.split("-") if part)


app = create_app()
