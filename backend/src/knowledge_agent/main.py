from pathlib import Path

from fastapi import FastAPI, HTTPException, status

from knowledge_agent.config import load_config
from knowledge_agent.db import connect, init_db
from knowledge_agent.import_service import import_pdf
from knowledge_agent.repositories import PapersRepository
from knowledge_agent.schemas import ImportPdfRequest, ImportPdfResponse, PapersResponse


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
