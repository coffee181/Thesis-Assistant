from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, status

from knowledge_agent.config import load_config
from knowledge_agent.db import connect, init_db
from knowledge_agent.import_service import import_pdf
from knowledge_agent.models import Chunk
from knowledge_agent.repositories import ChunksRepository, DocumentsRepository, PapersRepository
from knowledge_agent.schemas import (
    ImportPdfRequest,
    ImportPdfResponse,
    LocalSearchResponse,
    PapersResponse,
    ReaderContextResponse,
    ReaderPageResponse,
)


def create_app(library_dir: Path | None = None) -> FastAPI:
    config = load_config(library_dir)
    config.library_dir.mkdir(parents=True, exist_ok=True)

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
