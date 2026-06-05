from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, status

from knowledge_agent.assistant import (
    ProviderConfigurationError,
    answer_current_paper_question,
)
from knowledge_agent.bibliography import (
    export_bibtex,
    export_ris,
    parse_bibliography,
)
from knowledge_agent.config import load_config
from knowledge_agent.db import connect, init_db
from knowledge_agent.import_service import import_pdf
from knowledge_agent.models import Chunk, ProviderSettings
from knowledge_agent.providers import ChatProvider, HttpChatProvider
from knowledge_agent.repositories import (
    ChunksRepository,
    DocumentsRepository,
    PapersRepository,
    SettingsRepository,
)
from knowledge_agent.schemas import (
    AskPaperQuestionRequest,
    AskPaperQuestionResponse,
    CitationResponse,
    ExportBibliographyResponse,
    ImportBibliographyRequest,
    ImportBibliographyResponse,
    ImportPdfRequest,
    ImportPdfResponse,
    LocalSearchResponse,
    PapersResponse,
    ProviderSettingsRequest,
    ProviderSettingsResponse,
    ReaderContextResponse,
    ReaderPageResponse,
)


def create_app(
    library_dir: Path | None = None,
    chat_provider: ChatProvider | None = None,
) -> FastAPI:
    config = load_config(library_dir)
    config.library_dir.mkdir(parents=True, exist_ok=True)
    resolved_chat_provider = chat_provider or HttpChatProvider()

    with connect(config.database_path) as conn:
        init_db(conn)

    app = FastAPI(title="Knowledge Agent Backend")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "knowledge-agent-backend"}

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
        "/api/imports/pdf",
        response_model=ImportPdfResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def import_pdf_endpoint(request: ImportPdfRequest) -> ImportPdfResponse:
        source_path = Path(request.source_path)
        if not source_path.exists():
            raise HTTPException(status_code=404, detail="source PDF not found")
        try:
            with connect(config.database_path) as conn:
                result = import_pdf(conn, config.library_dir, source_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ImportPdfResponse(
            imported=result.imported,
            paper=result.paper,
            document=result.document,
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

    return app


app = create_app()


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
