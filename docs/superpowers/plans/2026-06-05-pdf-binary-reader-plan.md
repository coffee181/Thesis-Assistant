# PDF Binary Reader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users open the managed-library PDF itself in the desktop reader pane while preserving extracted text for assistant context and selected-text workflows.

**Architecture:** Add a backend file-serving endpoint that resolves a paper's current document path under the active managed library and refuses paths outside that library. The desktop app derives a stable PDF URL from the paper ID and embeds it in the reader pane with the existing extracted text shown below as the selectable context layer. This slice uses the WebView/browser native PDF viewer; PDF.js canvas controls and coordinate highlights remain a later reader enhancement.

**Tech Stack:** Python 3.13, FastAPI `FileResponse`, SQLite, pytest, React, TypeScript, Vitest, Testing Library.

---

## Scope

This plan implements:

- `GET /api/papers/{paper_id}/pdf` for serving the current paper PDF from the active managed library.
- Path containment checks so only files under the managed library can be served.
- Desktop PDF preview in the reader pane after opening a paper.
- Existing extracted text remains visible and selectable for translation, explanation, highlighting, notes, and current-paper Q&A.

This plan does not implement PDF.js canvas rendering, PDF toolbar controls, page thumbnails, native filesystem pickers, PDF coordinate-based highlights, scrolling synchronization between citations and PDF pages, or background parsing jobs.

## File Structure

Create or modify:

```text
backend/
  src/knowledge_agent/
    main.py
  tests/
    test_api.py
apps/
  desktop/
    src/
      App.test.tsx
      App.tsx
      api.ts
      styles.css
README.md
docs/
  superpowers/plans/2026-06-05-pdf-binary-reader-plan.md
```

Responsibilities:

- `backend/src/knowledge_agent/main.py`: Add the PDF file endpoint and private helper for safe managed-library path resolution.
- `backend/tests/test_api.py`: Prove the endpoint streams imported PDFs, reports missing papers, and refuses document paths outside the active managed library.
- `apps/desktop/src/api.ts`: Add a typed `paperPdfUrl(paperId)` URL helper.
- `apps/desktop/src/App.tsx`: Embed the PDF URL in the reader pane when a paper is open, while retaining the extracted text layer.
- `apps/desktop/src/styles.css`: Size the PDF preview and extracted text layer without breaking the three-pane layout.
- `README.md`: Mention that the reader now opens the managed-library PDF preview.

## Task 1: Backend PDF File Endpoint

**Files:**
- Modify: `backend/src/knowledge_agent/main.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Add these tests to `backend/tests/test_api.py` near the existing reader-context API tests:

```python
def test_paper_pdf_endpoint_streams_managed_pdf(tmp_path: Path, write_pdf):
    source = write_pdf(tmp_path / "Readable Paper.pdf", ["Readable page text."])
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))
    import_response = client.post("/api/imports/pdf", json={"source_path": str(source)})
    paper_id = import_response.json()["paper"]["id"]

    response = client.get(f"/api/papers/{paper_id}/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "readable-paper.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_paper_pdf_endpoint_reports_missing_paper(tmp_path: Path):
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))

    response = client.get("/api/papers/999/pdf")

    assert response.status_code == 404
    assert response.json()["detail"] == "paper not found"


def test_paper_pdf_endpoint_rejects_document_path_outside_library(
    tmp_path: Path,
    write_pdf,
):
    source = write_pdf(tmp_path / "Unsafe Paper.pdf", ["Unsafe page text."])
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))
    import_response = client.post("/api/imports/pdf", json={"source_path": str(source)})
    paper_id = import_response.json()["paper"]["id"]
    outside_pdf = tmp_path / "outside.pdf"
    outside_pdf.write_bytes(source.read_bytes())
    with connect(library_dir / "database.sqlite") as conn:
        conn.execute(
            "update documents set library_path = ? where paper_id = ?",
            ("../outside.pdf", paper_id),
        )

    response = client.get(f"/api/papers/{paper_id}/pdf")

    assert response.status_code == 404
    assert response.json()["detail"] == "PDF file not found"
```

Update test imports at the top of `backend/tests/test_api.py`:

```python
from knowledge_agent.db import connect as real_connect
```

to:

```python
from knowledge_agent.db import connect, connect as real_connect
```

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py::test_paper_pdf_endpoint_streams_managed_pdf backend/tests/test_api.py::test_paper_pdf_endpoint_reports_missing_paper backend/tests/test_api.py::test_paper_pdf_endpoint_rejects_document_path_outside_library -q
```

Expected: FAIL because `/api/papers/{paper_id}/pdf` does not exist.

- [ ] **Step 2: Implement safe PDF file serving**

In `backend/src/knowledge_agent/main.py`, add the response import:

```python
from fastapi.responses import FileResponse
```

Add this endpoint immediately after `get_reader_context`:

```python
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

        pdf_path = _managed_document_path(active_config.library_dir, document.library_path)
        if pdf_path is None or not pdf_path.exists() or not pdf_path.is_file():
            raise HTTPException(status_code=404, detail="PDF file not found")

        filename = f"{_slugify(paper.title) or 'paper'}.pdf"
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=filename,
        )
```

Add this helper near the other private helpers:

```python
def _managed_document_path(library_dir: Path, library_path: str) -> Path | None:
    library_root = library_dir.resolve()
    candidate = (library_root / library_path).resolve()
    if candidate == library_root or library_root not in candidate.parents:
        return None
    return candidate
```

- [ ] **Step 3: Verify backend PDF endpoint tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py::test_paper_pdf_endpoint_streams_managed_pdf backend/tests/test_api.py::test_paper_pdf_endpoint_reports_missing_paper backend/tests/test_api.py::test_paper_pdf_endpoint_rejects_document_path_outside_library -q
```

Expected: PASS.

- [ ] **Step 4: Verify backend API tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/src/knowledge_agent/main.py backend/tests/test_api.py
git commit -m "feat: serve managed paper PDFs"
```

## Task 2: Desktop PDF Preview

**Files:**
- Modify: `apps/desktop/src/api.ts`
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Write failing frontend test**

Add a test to `apps/desktop/src/App.test.tsx` near `opens a paper and displays reader context for the assistant`:

```tsx
  it("opens the managed PDF preview while keeping extracted text selectable", async () => {
    queueInitialReaderLoad();
    queueOpenReaderContext();

    await openReaderPaper();

    const preview = await screen.findByTitle("PDF reader for Reader Paper");
    expect(preview).toHaveAttribute(
      "src",
      "http://127.0.0.1:8765/api/papers/1/pdf",
    );
    expect(await screen.findByText("The method uses retrieval augmented generation.")).toBeInTheDocument();
  });
```

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test -- --run src/App.test.tsx -t "opens the managed PDF preview"
```

Expected: FAIL because the PDF preview iframe and URL helper do not exist.

- [ ] **Step 2: Implement API URL helper**

Add this function to `apps/desktop/src/api.ts` after `getReaderContext`:

```ts
export function paperPdfUrl(paperId: number): string {
  return `${API_BASE}/api/papers/${paperId}/pdf`;
}
```

- [ ] **Step 3: Implement reader preview UI**

In `apps/desktop/src/App.tsx`, import the helper:

```ts
  paperPdfUrl,
```

Replace the reader pane body with this structure:

```tsx
        {readerContext === null ? (
          <p className="empty">No paper open.</p>
        ) : (
          <div className="reader-content">
            <iframe
              className="pdf-preview"
              src={paperPdfUrl(readerContext.paper.id)}
              title={`PDF reader for ${readerContext.paper.title}`}
            />
            <section className="extracted-text-layer" aria-label="Extracted text">
              {readerContext.pages.length === 0 ? (
                <p className="empty">No extracted text available.</p>
              ) : (
                readerContext.pages.map((page) => (
                  <article
                    className="reader-page"
                    key={page.page_number}
                    onMouseUp={() => handleReaderPageMouseUp(page.page_number)}
                  >
                    <h3>Page {page.page_number}</h3>
                    <p>{page.text}</p>
                  </article>
                ))
              )}
            </section>
          </div>
        )}
```

Keep the existing toolbar heading unchanged.

- [ ] **Step 4: Style the PDF preview**

Add to `apps/desktop/src/styles.css`:

```css
.reader-content {
  display: grid;
  gap: 16px;
}

.pdf-preview {
  background: #ffffff;
  border: 1px solid #d7dde5;
  border-radius: 8px;
  box-sizing: border-box;
  min-height: 620px;
  width: 100%;
}

.extracted-text-layer {
  display: grid;
  gap: 10px;
}
```

In the existing mobile media query, add:

```css
  .pdf-preview {
    min-height: 520px;
  }
```

- [ ] **Step 5: Verify frontend test passes**

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test -- --run src/App.test.tsx -t "opens the managed PDF preview"
```

Expected: PASS.

- [ ] **Step 6: Verify desktop tests and build pass**

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm run build
```

Expected: both commands exit 0.

- [ ] **Step 7: Commit**

```powershell
git add apps/desktop/src/api.ts apps/desktop/src/App.test.tsx apps/desktop/src/App.tsx apps/desktop/src/styles.css
git commit -m "feat: preview managed PDFs in reader"
```

## Task 3: Documentation and Final Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

In `README.md`, update the Current Slice bullet:

```markdown
- PDF text reader context.
```

to:

```markdown
- Managed PDF preview with extracted text reader context.
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
git commit -m "docs: update PDF reader workflow"
```

## Self-Review Notes

- Spec coverage: This plan directly improves MVP acceptance criterion 6 by opening the managed PDF itself in the reader pane. It preserves existing support for criteria 7 through 10 by keeping extracted text selectable and available for assistant context.
- Placeholder scan: No `TBD`, `TODO`, or unspecified commands remain.
- Type consistency: The backend endpoint path is `/api/papers/{paper_id}/pdf`; the desktop helper is `paperPdfUrl(paperId)` and returns the same URL.
