from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Knowledge Agent Backend")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "knowledge-agent-backend"}

    return app


app = create_app()
