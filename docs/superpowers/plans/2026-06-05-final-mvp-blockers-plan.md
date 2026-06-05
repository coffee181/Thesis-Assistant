# Final MVP Blockers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the final review blockers that prevent marking the Windows desktop MVP complete.

**Architecture:** Keep fixes narrow: enable localhost CORS at the FastAPI boundary, make PDF import reuse existing metadata records before inserting a new paper, and add the Tauri icon assets required by the Windows shell build. No later-MVP features are added.

**Tech Stack:** FastAPI, pytest, SQLite repositories, Tauri v2, Cargo.

---

### Task 1: Backend CORS

**Files:**
- Modify: `backend/src/knowledge_agent/main.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: Write the failing CORS test**

Add a test that sends a browser-style preflight request from the Vite dev origin and expects the backend to allow it.

- [ ] **Step 2: Run the test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest backend/tests/test_api.py::test_backend_allows_localhost_desktop_cors -q`

Expected: FAIL because `OPTIONS /api/imports/pdf` is not handled by CORS.

- [ ] **Step 3: Enable localhost CORS**

Add FastAPI `CORSMiddleware` for localhost development and Tauri/webview origins.

- [ ] **Step 4: Run the CORS test**

Run: `.\.venv\Scripts\python -m pytest backend/tests/test_api.py::test_backend_allows_localhost_desktop_cors -q`

Expected: PASS.

### Task 2: Import Existing Metadata PDF

**Files:**
- Modify: `backend/src/knowledge_agent/import_service.py`
- Modify: `backend/src/knowledge_agent/repositories.py`
- Test: `backend/tests/test_import_service.py`

- [ ] **Step 1: Write the failing DOI reuse test**

Add a test where BibTeX/RIS-style metadata creates a paper with a DOI, then a PDF with the same DOI metadata is imported.

- [ ] **Step 2: Run the test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest backend/tests/test_import_service.py::test_import_pdf_attaches_document_to_existing_metadata_doi -q`

Expected: FAIL with a SQLite unique DOI constraint error.

- [ ] **Step 3: Reuse the existing metadata paper**

Teach the import path to locate an existing paper by DOI, citation key, or title/year before inserting a new paper, then create the document for that paper.

- [ ] **Step 4: Run the DOI reuse test**

Run: `.\.venv\Scripts\python -m pytest backend/tests/test_import_service.py::test_import_pdf_attaches_document_to_existing_metadata_doi -q`

Expected: PASS.

### Task 3: Tauri Windows Shell Build

**Files:**
- Create: `apps/desktop/src-tauri/icons/icon.ico`
- Create: `apps/desktop/src-tauri/icons/icon.png`
- Modify: `apps/desktop/src-tauri/tauri.conf.json`
- Create: `apps/desktop/src-tauri/Cargo.lock`

- [ ] **Step 1: Reproduce the shell build failure**

Run: `cargo check` from `apps/desktop/src-tauri`.

Expected: FAIL because `icons/icon.ico` is missing.

- [ ] **Step 2: Add minimal icon assets**

Create local app icon assets and configure Tauri to use them.

- [ ] **Step 3: Run shell build verification**

Run: `cargo check` from `apps/desktop/src-tauri`.

Expected: PASS.

### Task 4: Final Verification

**Files:**
- No additional edits unless verification exposes a regression.

- [ ] **Step 1: Run backend tests**

Run: `.\.venv\Scripts\python -m pytest backend/tests -q`

Expected: PASS.

- [ ] **Step 2: Run frontend tests**

Run: `$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test` from `apps/desktop`

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run: `$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm run build` from `apps/desktop`

Expected: PASS.

- [ ] **Step 4: Commit**

Commit message: `fix: resolve final MVP blockers`
