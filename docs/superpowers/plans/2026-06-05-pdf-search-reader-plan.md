# PDF Search and Reader Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make imported PDFs extractable, searchable, and readable enough for the assistant to automatically use the current paper context.

**Architecture:** Extend the existing FastAPI + SQLite backend with extracted page chunks and a local keyword search boundary. Keep parsing synchronous for this MVP slice so imported valid PDFs become searchable immediately, while parse failures remain recoverable and do not break import. Extend the React desktop shell into a three-pane workbench with library/search, a text-based paper reader, and a right-side assistant context panel.

**Tech Stack:** Python 3.13, FastAPI, SQLite, pypdf, pytest, ReportLab for PDF fixtures, React, TypeScript, Vitest, Testing Library.

---

## Scope

This plan implements PDF text extraction, source-spanned page chunks, local keyword search over titles and extracted chunks, and a current-paper reader context endpoint. It does not implement LLM provider calls, semantic/vector search, external paper discovery, open-access downloads, highlights, notes, or binary PDF canvas rendering.

## File Structure

Create or modify these files:

```text
backend/
  pyproject.toml
  src/knowledge_agent/
    db.py
    import_service.py
    main.py
    models.py
    pdf_text.py
    repositories.py
    schemas.py
  tests/
    conftest.py
    test_api.py
    test_database.py
    test_import_service.py
    test_pdf_text.py
apps/
  desktop/
    src/
      App.test.tsx
      App.tsx
      api.ts
      styles.css
docs/
  superpowers/plans/2026-06-05-pdf-search-reader-plan.md
```

Responsibilities:

- `backend/src/knowledge_agent/pdf_text.py`: Extract page text with pypdf and split pages into source-spanned chunks.
- `backend/src/knowledge_agent/db.py`: Add `chunks` and `chunks_fts`; add document parse status columns.
- `backend/src/knowledge_agent/repositories.py`: Add chunk replacement/list/search operations and document parse updates.
- `backend/src/knowledge_agent/import_service.py`: Parse valid imported PDFs synchronously and store chunks; preserve import if parsing fails.
- `backend/src/knowledge_agent/main.py`: Add local search and reader context APIs.
- `apps/desktop/src/api.ts`: Add typed search and reader context calls.
- `apps/desktop/src/App.tsx`: Add local search, paper selection, text reader, and assistant context panel.

## Task 1: Chunk Schema and Repository Layer

**Files:**
- Modify: `backend/src/knowledge_agent/db.py`
- Modify: `backend/src/knowledge_agent/models.py`
- Modify: `backend/src/knowledge_agent/repositories.py`
- Modify: `backend/tests/test_database.py`

- [ ] **Step 1: Write failing repository tests**

Add tests proving the database creates chunk storage, replaces chunks for a document, and finds keyword hits with paper/page/snippet evidence.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py -q
```

Expected: FAIL because chunk models and repository methods are missing.

- [ ] **Step 2: Implement minimal schema and repository code**

Add:

- `documents.parse_status text not null default 'pending'`
- `documents.parse_error text`
- `chunks` table with paper/document/page/chunk/source span fields
- `chunks_fts` FTS5 table for chunk keyword search
- `Chunk`, `ChunkInput`, and `SearchHit` dataclasses
- `DocumentsRepository.update_parse_result`
- `ChunksRepository.replace_for_document`, `list_for_paper`, and `search`

- [ ] **Step 3: Verify repository tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add backend/src/knowledge_agent/db.py backend/src/knowledge_agent/models.py backend/src/knowledge_agent/repositories.py backend/tests/test_database.py
git commit -m "feat: add searchable document chunks"
```

## Task 2: PDF Text Extraction During Import

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_pdf_text.py`
- Modify: `backend/tests/test_import_service.py`
- Create: `backend/src/knowledge_agent/pdf_text.py`
- Modify: `backend/src/knowledge_agent/import_service.py`

- [ ] **Step 1: Write failing PDF extraction tests**

Add tests that generate a small PDF fixture, extract page text, create page-numbered chunks, and assert import stores chunks plus `page_count`.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_pdf_text.py backend/tests/test_import_service.py -q
```

Expected: FAIL because `knowledge_agent.pdf_text` and import-time parsing are missing.

- [ ] **Step 2: Add dependencies**

Add production dependency:

```toml
"pypdf>=5.0.0"
```

Add dev dependency:

```toml
"reportlab>=4.2.0"
```

Install:

```powershell
.\.venv\Scripts\python -m pip install -e "backend[dev]"
```

- [ ] **Step 3: Implement minimal PDF extraction and chunking**

Implement `extract_pdf_pages(pdf_path: Path) -> list[ExtractedPage]` and `chunk_pages(pages: list[ExtractedPage], max_chars: int = 1200, overlap: int = 120) -> list[ChunkInput]`.

Behavior:

- Page numbers are 1-based.
- Empty pages produce no chunks.
- Text whitespace is normalized.
- `source_span` is `page:<page_number>:chars:<start>-<end>`.

- [ ] **Step 4: Wire parsing into import**

After copying a new PDF and creating its document record, extract pages, store chunks, and update `documents.page_count` and `documents.parse_status` to `parsed`. If extraction raises an exception, keep the imported PDF and set `parse_status` to `failed` with a short error string.

- [ ] **Step 5: Verify PDF extraction tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_pdf_text.py backend/tests/test_import_service.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/pyproject.toml backend/src/knowledge_agent/pdf_text.py backend/src/knowledge_agent/import_service.py backend/tests/conftest.py backend/tests/test_pdf_text.py backend/tests/test_import_service.py
git commit -m "feat: extract text from imported pdfs"
```

## Task 3: Search and Reader Context APIs

**Files:**
- Modify: `backend/src/knowledge_agent/schemas.py`
- Modify: `backend/src/knowledge_agent/main.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Add tests for:

- `GET /api/search/local?q=<term>` returns paper/page/snippet hits.
- `GET /api/papers/{paper_id}/reader-context` returns paper metadata, document parse status, and page text grouped by page.
- Missing paper returns 404.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py -q
```

Expected: FAIL because the endpoints are missing.

- [ ] **Step 2: Implement schemas and endpoints**

Add response models:

- `SearchHitResponse`
- `LocalSearchResponse`
- `ReaderPageResponse`
- `ReaderContextResponse`

Add endpoints:

- `GET /api/search/local`
- `GET /api/papers/{paper_id}/reader-context`

- [ ] **Step 3: Verify API tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add backend/src/knowledge_agent/schemas.py backend/src/knowledge_agent/main.py backend/tests/test_api.py
git commit -m "feat: expose local search and reader context"
```

## Task 4: Desktop Search and Reader Context UI

**Files:**
- Modify: `apps/desktop/src/api.ts`
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Write failing frontend tests**

Add tests proving the app can:

- Search the local library and display page-numbered hits.
- Open a paper and display extracted page text.
- Show the assistant panel is using the selected paper context.

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
```

Expected: FAIL because search and reader UI are missing.

- [ ] **Step 2: Implement API client types and calls**

Add:

- `searchLocal(query: string)`
- `getReaderContext(paperId: number)`
- response types for search hits and reader context.

- [ ] **Step 3: Implement the UI**

Reshape the app into:

- Left pane: backend status, import form, local search, paper list, search hits.
- Center pane: selected paper title and extracted page text.
- Right pane: assistant context status showing the current paper and parse status.

- [ ] **Step 4: Verify frontend tests pass**

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add apps/desktop/src/api.ts apps/desktop/src/App.test.tsx apps/desktop/src/App.tsx apps/desktop/src/styles.css
git commit -m "feat: add desktop reader context workflow"
```

## Final Verification

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm run build
```

Expected: all commands exit 0.

Commit any plan checkbox updates or documentation changes with the closest related task commit.

