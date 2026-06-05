# Library Setup and Folder Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a Windows user see/select the active managed library directory and import a folder of PDFs into that local library.

**Architecture:** Keep the Python backend as the source of truth for the active library path. Add a mutable app-level library config in `create_app`, expose library status and selection endpoints, add a recursive folder import service on top of the existing hash-deduplicating `import_pdf`, then surface those controls in the desktop sidebar.

**Tech Stack:** Python 3.13, FastAPI, SQLite, pytest, React, TypeScript, Vitest, Testing Library.

---

## Scope

This plan implements:

- `GET /api/library` for active managed library status.
- `PUT /api/library` for selecting or creating a managed library directory during the backend process lifetime.
- `POST /api/imports/folder` for recursive PDF folder import.
- Desktop display of the active library path.
- Desktop managed-library path form.
- Desktop folder import form with imported/skipped/failed counts.

This plan does not implement a native Windows folder picker, persisted cross-process library preferences outside `KA_LIBRARY_DIR`, background jobs, progress streaming, metadata matching during folder import, or PDF.js rendering.

## File Structure

Create or modify:

```text
backend/
  src/knowledge_agent/
    import_service.py
    main.py
    schemas.py
  tests/
    test_api.py
    test_import_service.py
apps/
  desktop/
    src/
      App.test.tsx
      App.tsx
      api.ts
      styles.css
README.md
docs/
  superpowers/plans/2026-06-05-library-folder-import-plan.md
```

Responsibilities:

- `backend/src/knowledge_agent/import_service.py`: Add `FolderImportResult`, `FolderImportFailure`, and `import_pdf_folder`.
- `backend/src/knowledge_agent/main.py`: Add library status/selection endpoints and folder import endpoint.
- `backend/src/knowledge_agent/schemas.py`: Add library and folder import request/response schemas.
- `apps/desktop/src/api.ts`: Add typed client methods for library status, library selection, and folder import.
- `apps/desktop/src/App.tsx`: Show active library path, switch path, and import folders.
- `apps/desktop/src/styles.css`: Keep new library controls compact and consistent.

## Task 1: Folder Import Service

**Files:**
- Modify: `backend/src/knowledge_agent/import_service.py`
- Modify: `backend/tests/test_import_service.py`

- [ ] **Step 1: Write failing service tests**

Add tests to `backend/tests/test_import_service.py`:

```python
def test_import_pdf_folder_recursively_imports_pdfs_and_skips_duplicates(tmp_path: Path):
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
```

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_import_service.py -q
```

Expected: FAIL because `import_pdf_folder` does not exist.

- [ ] **Step 2: Implement folder import service**

Add dataclasses:

```python
@dataclass(frozen=True)
class FolderImportFailure:
    source_path: str
    error: str


@dataclass(frozen=True)
class FolderImportResult:
    source_path: str
    discovered_count: int
    imported_count: int
    skipped_count: int
    failed_count: int
    imports: list[ImportResult]
    failures: list[FolderImportFailure]
```

Add:

```python
def import_pdf_folder(
    conn: sqlite3.Connection,
    library_root: Path,
    source_dir: Path,
) -> FolderImportResult:
    source_dir = source_dir.resolve()
    if not source_dir.exists():
        raise FileNotFoundError(source_dir)
    if not source_dir.is_dir():
        raise ValueError("source path is not a folder")

    pdf_paths = sorted(
        (path for path in source_dir.rglob("*") if path.suffix.lower() == ".pdf"),
        key=lambda path: path.as_posix().lower(),
    )
    imports: list[ImportResult] = []
    failures: list[FolderImportFailure] = []
    imported_count = 0
    skipped_count = 0

    for pdf_path in pdf_paths:
        try:
            result = import_pdf(conn, library_root, pdf_path)
        except Exception as exc:
            failures.append(
                FolderImportFailure(
                    source_path=str(pdf_path),
                    error=str(exc)[:500],
                )
            )
            continue
        imports.append(result)
        if result.imported:
            imported_count += 1
        else:
            skipped_count += 1

    return FolderImportResult(
        source_path=str(source_dir),
        discovered_count=len(pdf_paths),
        imported_count=imported_count,
        skipped_count=skipped_count,
        failed_count=len(failures),
        imports=imports,
        failures=failures,
    )
```

- [ ] **Step 3: Verify service tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_import_service.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add backend/src/knowledge_agent/import_service.py backend/tests/test_import_service.py
git commit -m "feat: import PDF folders"
```

## Task 2: Library and Folder Import APIs

**Files:**
- Modify: `backend/src/knowledge_agent/main.py`
- Modify: `backend/src/knowledge_agent/schemas.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Add tests to `backend/tests/test_api.py`:

```python
def test_library_endpoint_reports_active_library_path(tmp_path: Path):
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))

    response = client.get("/api/library")

    assert response.status_code == 200
    assert response.json()["library_dir"] == str(library_dir)
    assert response.json()["database_path"] == str(library_dir / "database.sqlite")
    assert response.json()["paper_count"] == 0


def test_select_library_switches_active_database(tmp_path: Path):
    first_library = tmp_path / "first-library"
    second_library = tmp_path / "second-library"
    source = tmp_path / "Paper.pdf"
    source.write_bytes(b"%PDF-1.4 paper")
    client = TestClient(create_app(library_dir=first_library))
    client.post("/api/imports/pdf", json={"source_path": str(source)})

    response = client.put("/api/library", json={"library_dir": str(second_library)})
    list_response = client.get("/api/papers")

    assert response.status_code == 200
    assert response.json()["library_dir"] == str(second_library)
    assert (second_library / "database.sqlite").exists()
    assert list_response.json()["papers"] == []


def test_import_folder_endpoint_imports_recursive_pdfs(tmp_path: Path):
    source_dir = tmp_path / "papers"
    nested = source_dir / "nested"
    nested.mkdir(parents=True)
    (source_dir / "First.pdf").write_bytes(b"%PDF-1.4 first")
    (nested / "Second.pdf").write_bytes(b"%PDF-1.4 second")
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))

    response = client.post("/api/imports/folder", json={"source_dir": str(source_dir)})
    list_response = client.get("/api/papers")

    assert response.status_code == 201
    payload = response.json()
    assert payload["discovered_count"] == 2
    assert payload["imported_count"] == 2
    assert payload["skipped_count"] == 0
    assert payload["failed_count"] == 0
    assert [paper["title"] for paper in list_response.json()["papers"]] == ["First", "Second"]


def test_import_folder_endpoint_reports_missing_folder(tmp_path: Path):
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))

    response = client.post(
        "/api/imports/folder",
        json={"source_dir": str(tmp_path / "missing")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "source folder not found"
```

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py -q
```

Expected: FAIL because the endpoints and schemas do not exist.

- [ ] **Step 2: Implement schemas**

Add to `backend/src/knowledge_agent/schemas.py`:

```python
class LibraryResponse(BaseModel):
    library_dir: str
    database_path: str
    paper_count: int


class SelectLibraryRequest(BaseModel):
    library_dir: str = Field(min_length=1)


class ImportFolderRequest(BaseModel):
    source_dir: str = Field(min_length=1)


class ImportFolderFailureResponse(BaseModel):
    source_path: str
    error: str


class ImportFolderResponse(BaseModel):
    source_path: str
    discovered_count: int
    imported_count: int
    skipped_count: int
    failed_count: int
    imports: list[ImportPdfResponse]
    failures: list[ImportFolderFailureResponse]
```

- [ ] **Step 3: Implement endpoints**

In `create_app`, allow `config` to be reassigned with `nonlocal config` inside `select_library`. Add helper:

```python
def _library_response(config: AppConfig) -> LibraryResponse:
    with connect(config.database_path) as conn:
        paper_count = len(PapersRepository(conn).list_all())
    return LibraryResponse(
        library_dir=str(config.library_dir),
        database_path=str(config.database_path),
        paper_count=paper_count,
    )
```

Add endpoints:

```python
@app.get("/api/library", response_model=LibraryResponse)
def get_library() -> LibraryResponse:
    return _library_response(config)


@app.put("/api/library", response_model=LibraryResponse)
def select_library(request: SelectLibraryRequest) -> LibraryResponse:
    nonlocal config
    selected = load_config(Path(request.library_dir))
    selected.library_dir.mkdir(parents=True, exist_ok=True)
    with connect(selected.database_path) as conn:
        init_db(conn)
    config = selected
    return _library_response(config)


@app.post(
    "/api/imports/folder",
    response_model=ImportFolderResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_folder_endpoint(request: ImportFolderRequest) -> ImportFolderResponse:
    source_dir = Path(request.source_dir)
    if not source_dir.exists():
        raise HTTPException(status_code=404, detail="source folder not found")
    try:
        with connect(config.database_path) as conn:
            result = import_pdf_folder(conn, config.library_dir, source_dir)
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
        failures=result.failures,
    )
```

- [ ] **Step 4: Verify API tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/src/knowledge_agent/main.py backend/src/knowledge_agent/schemas.py backend/tests/test_api.py
git commit -m "feat: expose library folder import api"
```

## Task 3: Desktop Library Controls

**Files:**
- Modify: `apps/desktop/src/api.ts`
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Write failing frontend tests**

Add tests to `apps/desktop/src/App.test.tsx` proving:

- Initial load calls `/api/library` and displays `Library: F:\KnowledgeAgentLibrary`.
- Setting a new library path calls `PUT /api/library`, displays the new path, and refreshes papers.
- Importing a folder calls `POST /api/imports/folder`, displays imported/skipped/failed counts, and refreshes papers.

Use mocked responses with this shape:

```ts
{ library_dir: "F:\\KnowledgeAgentLibrary", database_path: "F:\\KnowledgeAgentLibrary\\database.sqlite", paper_count: 0 }
```

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
```

Expected: FAIL because the desktop API client and UI do not exist.

- [ ] **Step 2: Implement API client calls**

Add types and functions:

```ts
export type LibraryStatus = {
  library_dir: string;
  database_path: string;
  paper_count: number;
};

export type ImportFolderResponse = {
  source_path: string;
  discovered_count: number;
  imported_count: number;
  skipped_count: number;
  failed_count: number;
  imports: ImportPdfResponse[];
  failures: { source_path: string; error: string }[];
};

export async function getLibrary(): Promise<LibraryStatus>;
export async function selectLibrary(libraryDir: string): Promise<LibraryStatus>;
export async function importFolder(sourceDir: string): Promise<ImportFolderResponse>;
```

- [ ] **Step 3: Implement desktop UI**

Update initial load to fetch library status before papers. Add:

- `libraryStatus`, `libraryPath`, `folderPath` state.
- `handleSelectLibrary` form submission.
- `handleFolderImport` form submission.
- A compact `Library location` panel at the top of the sidebar.
- A `PDF folder path` input with `Import folder` button.

Messages:

- Select library success: `Library selected`
- Folder import success: `Folder imported: {imported_count} imported, {skipped_count} skipped, {failed_count} failed`

- [ ] **Step 4: Verify frontend tests pass**

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add apps/desktop/src/api.ts apps/desktop/src/App.test.tsx apps/desktop/src/App.tsx apps/desktop/src/styles.css
git commit -m "feat: add desktop library folder import"
```

## Task 4: Documentation and Final Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

Update Current Slice to include:

- Active managed library status and selection.
- Recursive folder PDF import.
- Selected-text translation/explanation.
- Notes and highlights.

Add a usage note:

```markdown
The backend defaults to `%USERPROFILE%\KnowledgeAgentLibrary`, or `KA_LIBRARY_DIR` when set. In the desktop app, paste a managed library path into `Library location` to switch the active local library for the running backend.
```

- [ ] **Step 2: Run final verification**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm run build
```

Expected: all commands exit 0.

- [ ] **Step 3: Commit**

```powershell
git add README.md
git commit -m "docs: update library workflow"
```

## Self-Review Notes

- Spec coverage: This plan covers MVP acceptance criteria 1 and the folder-PDF part of criterion 2 while preserving the already implemented single-PDF, BibTeX/RIS, search, reader, Q&A, selected text, notes, and highlights workflows.
- Placeholder scan: No placeholder markers or unspecified test commands remain.
- Type consistency: Request fields use `library_dir` and `source_dir`; response fields use `library_dir`, `database_path`, count fields, `imports`, and `failures` consistently across backend and frontend.
