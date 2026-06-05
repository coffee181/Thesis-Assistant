# Knowledge Agent Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working vertical slice: a Windows-first desktop shell connected to a local Python backend that can initialize a managed library, import PDF files by path, deduplicate by hash, and list imported papers.

**Architecture:** Create a monorepo with `backend/` for FastAPI + SQLite and `apps/desktop/` for Vite React + Tauri. The first slice runs the backend as a local development process and has the desktop UI talk to `http://127.0.0.1:8765`; Tauri sidecar packaging is left for a later packaging plan after the backend interface stabilizes.

**Tech Stack:** Python 3.13, FastAPI, pytest, httpx, SQLite, Node 24, npm, React, TypeScript, Vite, Vitest, Tauri 2, Rust/Cargo.

---

## Scope

This plan implements the foundation only. It does not implement PDF rendering, PDF text extraction, RAG, embeddings, external metadata search, open-access download, notes, or highlights. Those are separate follow-up plans once this foundation is running.

## File Structure

Create this structure:

```text
backend/
  pyproject.toml
  src/knowledge_agent/
    __init__.py
    config.py
    db.py
    import_service.py
    main.py
    models.py
    repositories.py
    schemas.py
  tests/
    test_api.py
    test_database.py
    test_health.py
    test_import_service.py
apps/
  desktop/
    index.html
    package.json
    tsconfig.json
    tsconfig.node.json
    vite.config.ts
    src/
      App.test.tsx
      App.tsx
      api.ts
      main.tsx
      styles.css
    src-tauri/
      Cargo.toml
      build.rs
      tauri.conf.json
      src/
        main.rs
scripts/
  dev-backend.ps1
  dev-desktop.ps1
README.md
```

Responsibilities:

- `backend/src/knowledge_agent/db.py`: SQLite connection and schema creation.
- `backend/src/knowledge_agent/repositories.py`: SQL operations for papers and documents.
- `backend/src/knowledge_agent/import_service.py`: managed library import, hashing, deduplication, and file copy.
- `backend/src/knowledge_agent/main.py`: FastAPI app factory and endpoints.
- `apps/desktop/src/api.ts`: typed frontend API calls.
- `apps/desktop/src/App.tsx`: minimal library UI that checks backend health, imports by local path, and lists papers.
- `apps/desktop/src-tauri/`: minimal Tauri wrapper around the Vite frontend.
- `scripts/`: Windows development entry points.

## Task 1: Backend Project and Health Endpoint

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/knowledge_agent/__init__.py`
- Create: `backend/src/knowledge_agent/main.py`
- Create: `backend/tests/test_health.py`

- [ ] **Step 1: Create backend project metadata**

Create `backend/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "knowledge-agent-backend"
version = "0.1.0"
description = "Local backend for Knowledge Agent"
requires-python = ">=3.13"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "pydantic>=2.8.0"
]

[project.optional-dependencies]
dev = [
  "httpx>=0.27.0",
  "pytest>=8.2.0",
  "pytest-cov>=5.0.0"
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-q"
```

Create `backend/src/knowledge_agent/__init__.py`:

```python
__all__ = ["__version__"]

__version__ = "0.1.0"
```

- [ ] **Step 2: Create the failing health test**

Create `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from knowledge_agent.main import create_app


def test_health_returns_ok():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "knowledge-agent-backend"}
```

- [ ] **Step 3: Install backend in editable mode**

Run:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e "backend[dev]"
```

Expected: pip installs FastAPI, pytest, and the local package without errors.

- [ ] **Step 4: Run the health test and verify it fails**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_health.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'knowledge_agent.main'`.

- [ ] **Step 5: Implement the health endpoint**

Create `backend/src/knowledge_agent/main.py`:

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Knowledge Agent Backend")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "knowledge-agent-backend"}

    return app


app = create_app()
```

- [ ] **Step 6: Run the health test and verify it passes**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_health.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add backend/pyproject.toml backend/src/knowledge_agent/__init__.py backend/src/knowledge_agent/main.py backend/tests/test_health.py
git commit -m "feat: add backend health endpoint"
```

## Task 2: SQLite Schema and Repository Layer

**Files:**
- Create: `backend/src/knowledge_agent/db.py`
- Create: `backend/src/knowledge_agent/models.py`
- Create: `backend/src/knowledge_agent/repositories.py`
- Create: `backend/tests/test_database.py`

- [ ] **Step 1: Write failing database tests**

Create `backend/tests/test_database.py`:

```python
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
```

- [ ] **Step 2: Run database tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py -q
```

Expected: FAIL with missing `knowledge_agent.db`.

- [ ] **Step 3: Implement data models**

Create `backend/src/knowledge_agent/models.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Paper:
    id: int
    title: str
    year: int | None
    doi: str | None
    created_at: str


@dataclass(frozen=True)
class Document:
    id: int
    paper_id: int
    library_path: str
    file_hash: str
    page_count: int | None
    created_at: str
```

- [ ] **Step 4: Implement SQLite connection and schema**

Create `backend/src/knowledge_agent/db.py`:

```python
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma foreign_keys = on")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        create table if not exists papers (
            id integer primary key autoincrement,
            title text not null,
            year integer,
            doi text,
            created_at text not null default current_timestamp
        );

        create unique index if not exists idx_papers_doi_unique
        on papers(doi)
        where doi is not null;

        create table if not exists documents (
            id integer primary key autoincrement,
            paper_id integer not null references papers(id) on delete cascade,
            library_path text not null,
            file_hash text not null unique,
            page_count integer,
            created_at text not null default current_timestamp
        );
        """
    )
```

- [ ] **Step 5: Implement repositories**

Create `backend/src/knowledge_agent/repositories.py`:

```python
import sqlite3

from knowledge_agent.models import Document, Paper


class PapersRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, title: str, year: int | None, doi: str | None) -> Paper:
        cursor = self._conn.execute(
            "insert into papers (title, year, doi) values (?, ?, ?)",
            (title, year, doi),
        )
        return self.get(cursor.lastrowid)

    def get(self, paper_id: int) -> Paper:
        row = self._conn.execute(
            "select id, title, year, doi, created_at from papers where id = ?",
            (paper_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"paper not found: {paper_id}")
        return Paper(**dict(row))

    def list_all(self) -> list[Paper]:
        rows = self._conn.execute(
            "select id, title, year, doi, created_at from papers order by created_at desc, id desc"
        ).fetchall()
        return [Paper(**dict(row)) for row in rows]


class DocumentsRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        paper_id: int,
        library_path: str,
        file_hash: str,
        page_count: int | None,
    ) -> Document:
        cursor = self._conn.execute(
            """
            insert into documents (paper_id, library_path, file_hash, page_count)
            values (?, ?, ?, ?)
            """,
            (paper_id, library_path, file_hash, page_count),
        )
        return self.get(cursor.lastrowid)

    def get(self, document_id: int) -> Document:
        row = self._conn.execute(
            """
            select id, paper_id, library_path, file_hash, page_count, created_at
            from documents
            where id = ?
            """,
            (document_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"document not found: {document_id}")
        return Document(**dict(row))

    def find_by_hash(self, file_hash: str) -> Document | None:
        row = self._conn.execute(
            """
            select id, paper_id, library_path, file_hash, page_count, created_at
            from documents
            where file_hash = ?
            """,
            (file_hash,),
        ).fetchone()
        return Document(**dict(row)) if row else None
```

- [ ] **Step 6: Run database tests and verify they pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add backend/src/knowledge_agent/db.py backend/src/knowledge_agent/models.py backend/src/knowledge_agent/repositories.py backend/tests/test_database.py
git commit -m "feat: add sqlite library schema"
```

## Task 3: Managed PDF Import Service

**Files:**
- Create: `backend/src/knowledge_agent/import_service.py`
- Create: `backend/tests/test_import_service.py`

- [ ] **Step 1: Write failing import service tests**

Create `backend/tests/test_import_service.py`:

```python
from pathlib import Path

from knowledge_agent.db import connect, init_db
from knowledge_agent.import_service import import_pdf


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
```

- [ ] **Step 2: Run import tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_import_service.py -q
```

Expected: FAIL with missing `knowledge_agent.import_service`.

- [ ] **Step 3: Implement the import service**

Create `backend/src/knowledge_agent/import_service.py`:

```python
import hashlib
import re
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from knowledge_agent.models import Document, Paper
from knowledge_agent.repositories import DocumentsRepository, PapersRepository


@dataclass(frozen=True)
class ImportResult:
    paper: Paper
    document: Document
    imported: bool


def import_pdf(conn: sqlite3.Connection, library_root: Path, source_path: Path) -> ImportResult:
    source_path = source_path.resolve()
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    if source_path.suffix.lower() != ".pdf":
        raise ValueError("only PDF files can be imported")

    file_hash = _sha256(source_path)
    papers = PapersRepository(conn)
    documents = DocumentsRepository(conn)

    existing = documents.find_by_hash(file_hash)
    if existing is not None:
        return ImportResult(
            paper=papers.get(existing.paper_id),
            document=existing,
            imported=False,
        )

    title = source_path.stem.strip()
    paper = papers.create(title=title, year=None, doi=None)
    target_relative = _target_relative_path(paper.id, title, file_hash)
    target_absolute = library_root / target_relative
    target_absolute.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_absolute)

    document = documents.create(
        paper_id=paper.id,
        library_path=target_relative.as_posix(),
        file_hash=file_hash,
        page_count=None,
    )
    return ImportResult(paper=paper, document=document, imported=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _target_relative_path(paper_id: int, title: str, file_hash: str) -> Path:
    slug = _slugify(title) or "untitled"
    short_hash = file_hash[:12]
    return Path("papers") / "unknown-year" / f"{slug}-{paper_id}-{short_hash}" / "paper.pdf"


def _slugify(value: str) -> str:
    lowered = value.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    return normalized.strip("-")
```

- [ ] **Step 4: Run import tests and verify they pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_import_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add backend/src/knowledge_agent/import_service.py backend/tests/test_import_service.py
git commit -m "feat: import pdfs into managed library"
```

## Task 4: Backend API for Papers and Imports

**Files:**
- Create: `backend/src/knowledge_agent/config.py`
- Create: `backend/src/knowledge_agent/schemas.py`
- Modify: `backend/src/knowledge_agent/main.py`
- Create: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_api.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from knowledge_agent.main import create_app


def test_import_pdf_endpoint_then_list_papers(tmp_path: Path):
    source = tmp_path / "Endpoint Paper.pdf"
    source.write_bytes(b"%PDF-1.4 endpoint pdf")
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))

    import_response = client.post(
        "/api/imports/pdf",
        json={"source_path": str(source)},
    )
    list_response = client.get("/api/papers")

    assert import_response.status_code == 201
    assert import_response.json()["imported"] is True
    assert import_response.json()["paper"]["title"] == "Endpoint Paper"
    assert list_response.status_code == 200
    assert list_response.json()["papers"][0]["title"] == "Endpoint Paper"


def test_import_pdf_endpoint_reports_missing_file(tmp_path: Path):
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))

    response = client.post(
        "/api/imports/pdf",
        json={"source_path": str(tmp_path / "missing.pdf")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "source PDF not found"
```

- [ ] **Step 2: Run API tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py -q
```

Expected: FAIL because `create_app()` does not accept `library_dir`.

- [ ] **Step 3: Add configuration helpers**

Create `backend/src/knowledge_agent/config.py`:

```python
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    library_dir: Path

    @property
    def database_path(self) -> Path:
        return self.library_dir / "database.sqlite"


def load_config(library_dir: Path | None = None) -> AppConfig:
    configured = library_dir or Path(
        os.environ.get("KA_LIBRARY_DIR", Path.home() / "KnowledgeAgentLibrary")
    )
    return AppConfig(library_dir=configured)
```

- [ ] **Step 4: Add API schemas**

Create `backend/src/knowledge_agent/schemas.py`:

```python
from pydantic import BaseModel, Field


class PaperResponse(BaseModel):
    id: int
    title: str
    year: int | None
    doi: str | None
    created_at: str


class DocumentResponse(BaseModel):
    id: int
    paper_id: int
    library_path: str
    file_hash: str
    page_count: int | None
    created_at: str


class ImportPdfRequest(BaseModel):
    source_path: str = Field(min_length=1)


class ImportPdfResponse(BaseModel):
    imported: bool
    paper: PaperResponse
    document: DocumentResponse


class PapersResponse(BaseModel):
    papers: list[PaperResponse]
```

- [ ] **Step 5: Replace FastAPI app with configured endpoints**

Replace `backend/src/knowledge_agent/main.py` with:

```python
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
```

- [ ] **Step 6: Run all backend tests and verify they pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add backend/src/knowledge_agent/config.py backend/src/knowledge_agent/schemas.py backend/src/knowledge_agent/main.py backend/tests/test_api.py
git commit -m "feat: expose library import api"
```

## Task 5: React Desktop UI Foundation

**Files:**
- Create: `apps/desktop/package.json`
- Create: `apps/desktop/index.html`
- Create: `apps/desktop/tsconfig.json`
- Create: `apps/desktop/tsconfig.node.json`
- Create: `apps/desktop/vite.config.ts`
- Create: `apps/desktop/src/api.ts`
- Create: `apps/desktop/src/App.test.tsx`
- Create: `apps/desktop/src/App.tsx`
- Create: `apps/desktop/src/main.tsx`
- Create: `apps/desktop/src/styles.css`

- [ ] **Step 1: Create frontend package metadata**

Create `apps/desktop/package.json`:

```json
{
  "name": "knowledge-agent-desktop",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest run",
    "tauri": "tauri"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.4.0",
    "typescript": "^5.5.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "@tauri-apps/cli": "^2.0.0",
    "@tauri-apps/api": "^2.0.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "jsdom": "^24.1.0",
    "vitest": "^2.0.0"
  }
}
```

Create `apps/desktop/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Knowledge Agent</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `apps/desktop/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

Create `apps/desktop/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

Create `apps/desktop/vite.config.ts`:

```typescript
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: [],
    globals: true,
  },
});
```

- [ ] **Step 2: Install frontend dependencies**

Run:

```powershell
cd apps\desktop
npm install
cd ..\..
```

Expected: `package-lock.json` is created under `apps/desktop/`.

- [ ] **Step 3: Write failing UI test**

Create `apps/desktop/src/App.test.tsx`:

```typescript
import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  fetchMock.mockReset();
});

describe("App", () => {
  it("loads backend status and papers", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [{ id: 1, title: "Paper A", year: null, doi: null, created_at: "now" }] }),
      });

    render(<App />);

    expect(await screen.findByText("Backend: ok")).toBeInTheDocument();
    expect(await screen.findByText("Paper A")).toBeInTheDocument();
  });

  it("imports a PDF by source path", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ imported: true, paper: { id: 2, title: "Imported", year: null, doi: null, created_at: "now" }, document: { id: 1, paper_id: 2, library_path: "papers/imported/paper.pdf", file_hash: "abc", page_count: null, created_at: "now" } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [{ id: 2, title: "Imported", year: null, doi: null, created_at: "now" }] }),
      });

    render(<App />);
    await userEvent.type(screen.getByLabelText("PDF source path"), "F:\\papers\\imported.pdf");
    await userEvent.click(screen.getByRole("button", { name: "Import PDF" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8765/api/imports/pdf",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(await screen.findByText("Imported")).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run UI test and verify it fails**

Run:

```powershell
cd apps\desktop
npm test
cd ..\..
```

Expected: FAIL because `src/App.tsx` does not exist.

- [ ] **Step 5: Implement typed API client**

Create `apps/desktop/src/api.ts`:

```typescript
const API_BASE = "http://127.0.0.1:8765";

export type Paper = {
  id: number;
  title: string;
  year: number | null;
  doi: string | null;
  created_at: string;
};

export type PapersResponse = {
  papers: Paper[];
};

export type HealthResponse = {
  status: string;
  service: string;
};

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) throw new Error("Backend health check failed");
  return response.json();
}

export async function listPapers(): Promise<PapersResponse> {
  const response = await fetch(`${API_BASE}/api/papers`);
  if (!response.ok) throw new Error("Could not load papers");
  return response.json();
}

export async function importPdf(sourcePath: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/imports/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_path: sourcePath }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Import failed" }));
    throw new Error(payload.detail ?? "Import failed");
  }
}
```

- [ ] **Step 6: Implement React UI**

Create `apps/desktop/src/App.tsx`:

```typescript
import { FormEvent, useEffect, useState } from "react";

import { getHealth, importPdf, listPapers, Paper } from "./api";
import "./styles.css";

export default function App() {
  const [backendStatus, setBackendStatus] = useState("checking");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [sourcePath, setSourcePath] = useState("");
  const [message, setMessage] = useState("");

  async function refreshPapers() {
    const response = await listPapers();
    setPapers(response.papers);
  }

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const health = await getHealth();
        if (!active) return;
        setBackendStatus(health.status);
        await refreshPapers();
      } catch (error) {
        if (!active) return;
        setBackendStatus("offline");
        setMessage(error instanceof Error ? error.message : "Backend unavailable");
      }
    }

    load();
    return () => {
      active = false;
    };
  }, []);

  async function handleImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    try {
      await importPdf(sourcePath);
      setSourcePath("");
      setMessage("PDF imported");
      await refreshPapers();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Import failed");
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <h1>Knowledge Agent</h1>
        <p className="status">Backend: {backendStatus}</p>
      </aside>

      <section className="content">
        <header className="toolbar">
          <h2>Library</h2>
        </header>

        <form className="import-form" onSubmit={handleImport}>
          <label htmlFor="source-path">PDF source path</label>
          <div className="import-row">
            <input
              id="source-path"
              value={sourcePath}
              onChange={(event) => setSourcePath(event.target.value)}
              placeholder="F:\\papers\\example.pdf"
            />
            <button type="submit" disabled={sourcePath.trim().length === 0}>
              Import PDF
            </button>
          </div>
        </form>

        {message ? <p className="message">{message}</p> : null}

        <div className="paper-list">
          {papers.length === 0 ? (
            <p className="empty">No papers imported yet.</p>
          ) : (
            papers.map((paper) => (
              <article className="paper-row" key={paper.id}>
                <h3>{paper.title}</h3>
                <p>{paper.doi ?? "No DOI"}</p>
              </article>
            ))
          )}
        </div>
      </section>
    </main>
  );
}
```

Create `apps/desktop/src/main.tsx`:

```typescript
import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

Create `apps/desktop/src/styles.css`:

```css
:root {
  color: #1f2937;
  background: #f8fafc;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

body {
  margin: 0;
}

button,
input {
  font: inherit;
}

.app-shell {
  display: grid;
  grid-template-columns: 240px 1fr;
  min-height: 100vh;
}

.sidebar {
  border-right: 1px solid #d7dde5;
  background: #ffffff;
  padding: 24px;
}

.sidebar h1 {
  font-size: 20px;
  margin: 0 0 16px;
}

.status {
  color: #475569;
  margin: 0;
}

.content {
  padding: 28px;
}

.toolbar {
  align-items: center;
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.toolbar h2 {
  font-size: 24px;
  margin: 0;
}

.import-form {
  background: #ffffff;
  border: 1px solid #d7dde5;
  border-radius: 8px;
  margin-bottom: 16px;
  padding: 16px;
}

.import-form label {
  display: block;
  font-weight: 600;
  margin-bottom: 8px;
}

.import-row {
  display: flex;
  gap: 8px;
}

.import-row input {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  flex: 1;
  padding: 10px 12px;
}

.import-row button {
  background: #1f2937;
  border: 0;
  border-radius: 6px;
  color: #ffffff;
  cursor: pointer;
  padding: 10px 14px;
}

.import-row button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.message {
  color: #334155;
}

.paper-list {
  display: grid;
  gap: 10px;
}

.paper-row {
  background: #ffffff;
  border: 1px solid #d7dde5;
  border-radius: 8px;
  padding: 14px 16px;
}

.paper-row h3 {
  font-size: 16px;
  margin: 0 0 6px;
}

.paper-row p,
.empty {
  color: #64748b;
  margin: 0;
}
```

- [ ] **Step 7: Run UI tests and verify they pass**

Run:

```powershell
cd apps\desktop
npm test
npm run build
cd ..\..
```

Expected: PASS for Vitest and successful Vite build.

- [ ] **Step 8: Commit**

Run:

```powershell
git add apps/desktop
git commit -m "feat: add desktop library shell"
```

## Task 6: Minimal Tauri Shell

**Files:**
- Create: `apps/desktop/src-tauri/Cargo.toml`
- Create: `apps/desktop/src-tauri/build.rs`
- Create: `apps/desktop/src-tauri/tauri.conf.json`
- Create: `apps/desktop/src-tauri/src/main.rs`

- [ ] **Step 1: Create Tauri Rust project files**

Create `apps/desktop/src-tauri/Cargo.toml`:

```toml
[package]
name = "knowledge-agent"
version = "0.1.0"
description = "Knowledge Agent desktop shell"
authors = ["Knowledge Agent"]
edition = "2021"

[build-dependencies]
tauri-build = { version = "2", features = [] }

[dependencies]
tauri = { version = "2", features = [] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

Create `apps/desktop/src-tauri/build.rs`:

```rust
fn main() {
    tauri_build::build()
}
```

Create `apps/desktop/src-tauri/src/main.rs`:

```rust
fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("failed to run Knowledge Agent");
}
```

Create `apps/desktop/src-tauri/tauri.conf.json`:

```json
{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "Knowledge Agent",
  "version": "0.1.0",
  "identifier": "com.knowledgeagent.desktop",
  "build": {
    "beforeDevCommand": "npm run dev",
    "devUrl": "http://127.0.0.1:5173",
    "beforeBuildCommand": "npm run build",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [
      {
        "title": "Knowledge Agent",
        "width": 1280,
        "height": 820,
        "minWidth": 1024,
        "minHeight": 700
      }
    ]
  },
  "bundle": {
    "active": true,
    "targets": "all"
  }
}
```

- [ ] **Step 2: Verify Tauri metadata**

Run:

```powershell
cd apps\desktop
npm run tauri -- info
cd ..\..
```

Expected: Tauri CLI prints environment information and exits successfully.

- [ ] **Step 3: Build the desktop frontend through Tauri config**

Run:

```powershell
cd apps\desktop
npm run build
cd ..\..
```

Expected: `apps/desktop/dist/` is created.

- [ ] **Step 4: Commit**

Run:

```powershell
git add apps/desktop/src-tauri
git commit -m "feat: add tauri desktop shell"
```

## Task 7: Development Scripts and Smoke Test Documentation

**Files:**
- Create: `scripts/dev-backend.ps1`
- Create: `scripts/dev-desktop.ps1`
- Create: `README.md`

- [ ] **Step 1: Create backend development script**

Create `scripts/dev-backend.ps1`:

```powershell
$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  python -m venv .venv
}

.\.venv\Scripts\python -m pip install -e "backend[dev]"

$env:KA_LIBRARY_DIR = Join-Path (Get-Location) ".local-library"
.\.venv\Scripts\python -m uvicorn knowledge_agent.main:app --host 127.0.0.1 --port 8765 --reload
```

- [ ] **Step 2: Create desktop development script**

Create `scripts/dev-desktop.ps1`:

```powershell
$ErrorActionPreference = "Stop"

Push-Location apps\desktop
try {
  if (-not (Test-Path ".\node_modules")) {
    npm install
  }
  npm run tauri -- dev
}
finally {
  Pop-Location
}
```

- [ ] **Step 3: Create README**

Create `README.md`:

```markdown
# Knowledge Agent

Knowledge Agent is a Windows-first local literature library and research assistant.

## Current Slice

This repository currently implements the project foundation:

- FastAPI backend health endpoint.
- SQLite managed library schema.
- PDF import by local path.
- Hash-based duplicate detection.
- Basic paper listing API.
- React library shell.
- Minimal Tauri desktop wrapper.

## Development

Prerequisites:

- Python 3.13
- Node.js 24 and npm
- Rust and Cargo

Start the backend in one PowerShell window:

```powershell
.\scripts\dev-backend.ps1
```

Start the desktop app in another PowerShell window:

```powershell
.\scripts\dev-desktop.ps1
```

The backend listens on `http://127.0.0.1:8765`.

## Tests

Backend:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
```

Frontend:

```powershell
cd apps\desktop
npm test
npm run build
```
```

- [ ] **Step 4: Add local development library to `.gitignore`**

Modify `.gitignore` so it contains:

```gitignore
.superpowers/
.local-library/
.venv/
apps/desktop/node_modules/
apps/desktop/dist/
apps/desktop/src-tauri/target/
```

- [ ] **Step 5: Run backend tests**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
```

Expected: PASS.

- [ ] **Step 6: Run frontend tests and build**

Run:

```powershell
cd apps\desktop
npm test
npm run build
cd ..\..
```

Expected: PASS and successful build.

- [ ] **Step 7: Run backend smoke test**

Run in one PowerShell window:

```powershell
.\scripts\dev-backend.ps1
```

Run in a second PowerShell window:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
```

Expected:

```powershell
status service
------ -------
ok     knowledge-agent-backend
```

- [ ] **Step 8: Commit**

Run:

```powershell
git add .gitignore README.md scripts/dev-backend.ps1 scripts/dev-desktop.ps1
git commit -m "docs: add foundation development workflow"
```

## Plan Self-Review

Spec coverage for this foundation slice:

- Desktop shape: covered by Tasks 5 and 6.
- Python local backend: covered by Tasks 1 through 4.
- Managed local library directory: covered by Tasks 3, 4, and 7.
- SQLite canonical metadata: covered by Task 2.
- PDF import and hash-based dedupe: covered by Task 3.
- Observable API boundary: covered by Task 4.
- Windows development path: covered by Task 7.

Requirements deferred to later plans:

- PDF rendering and selected-text reading.
- Text extraction and chunk source spans.
- Full-text indexing.
- Vector indexing.
- Traceable assistant and model providers.
- External metadata search and open-access downloads.
- Notes and highlights.
- Tauri sidecar packaging of the Python backend.

The deferred items are outside this foundation slice and remain covered by the approved design spec.
