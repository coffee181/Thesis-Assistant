# Tags and Favorites Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add lightweight paper organization through favorites, tags, and library filters.

**Architecture:** Store favorite status on `papers`, store reusable tag names in `tags`, and connect papers to tags through `paper_tags`. The backend returns favorite and tag data with each paper; the desktop app lets users toggle favorites, add/remove tags, and filter the visible library by favorite/tag without changing reader behavior.

**Tech Stack:** FastAPI, SQLite, pytest, React, TypeScript, Vitest.

---

### Task 1: Backend Tags and Favorites

**Files:**
- Modify: `backend/src/knowledge_agent/db.py`
- Modify: `backend/src/knowledge_agent/models.py`
- Modify: `backend/src/knowledge_agent/repositories.py`
- Modify: `backend/src/knowledge_agent/schemas.py`
- Modify: `backend/src/knowledge_agent/main.py`
- Test: `backend/tests/test_database.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing repository tests**

Add tests proving:
- `papers.favorite` defaults to `False`.
- `PapersRepository.set_favorite()` updates the paper and filtered lists.
- `PapersRepository.add_tag()` creates/reuses tags and attaches names to returned papers.
- `PapersRepository.remove_tag()` detaches a tag.
- `PapersRepository.merge_papers()` preserves tags when duplicate paper records are merged.

- [ ] **Step 2: Run repository tests to verify RED**

Run: `.\.venv\Scripts\python -m pytest backend/tests/test_database.py::test_paper_favorite_roundtrip_and_filter backend/tests/test_database.py::test_paper_tags_roundtrip_and_filter backend/tests/test_database.py::test_merge_papers_preserves_tags -q`

Expected: FAIL because favorite/tag APIs do not exist.

- [ ] **Step 3: Write failing API tests**

Add tests proving:
- `PUT /api/papers/{paper_id}/favorite` returns the updated paper.
- `POST /api/papers/{paper_id}/tags` returns the paper with the new tag.
- `DELETE /api/papers/{paper_id}/tags/{tag_name}` returns the paper without that tag.
- `GET /api/papers?favorite=true&tag=reading` filters the library.

- [ ] **Step 4: Run API tests to verify RED**

Run: `.\.venv\Scripts\python -m pytest backend/tests/test_api.py::test_paper_favorite_endpoint_filters_library backend/tests/test_api.py::test_paper_tags_endpoints_roundtrip -q`

Expected: FAIL because endpoints and schema fields do not exist.

- [ ] **Step 5: Implement backend support**

Add the SQLite schema, repository methods, schemas, and FastAPI endpoints needed by the tests. Keep tag names trimmed; reject empty tag names with `400`.

- [ ] **Step 6: Run backend tests to verify GREEN**

Run: `.\.venv\Scripts\python -m pytest backend/tests/test_database.py::test_paper_favorite_roundtrip_and_filter backend/tests/test_database.py::test_paper_tags_roundtrip_and_filter backend/tests/test_database.py::test_merge_papers_preserves_tags backend/tests/test_api.py::test_paper_favorite_endpoint_filters_library backend/tests/test_api.py::test_paper_tags_endpoints_roundtrip -q`

Expected: PASS.

### Task 2: Desktop Tags and Favorites

**Files:**
- Modify: `apps/desktop/src/api.ts`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Write failing desktop tests**

Add tests proving:
- Clicking a paper's favorite control calls `PUT /api/papers/{id}/favorite` and refreshes the library.
- Adding a tag calls `POST /api/papers/{id}/tags` and displays the tag after refresh.
- Applying favorite/tag filters calls `GET /api/papers?favorite=true&tag=reading`.

- [ ] **Step 2: Run desktop tests to verify RED**

Run: `$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test -- -t "paper organization"`

Expected: FAIL because controls and API helpers do not exist.

- [ ] **Step 3: Implement desktop support**

Add API helpers, library filters, favorite button, tag input, tag display, and remove-tag controls while keeping the existing paper open button accessible.

- [ ] **Step 4: Run desktop tests to verify GREEN**

Run: `$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test -- -t "paper organization"`

Expected: PASS.

### Task 3: Verification and Commit

**Files:**
- No additional edits unless verification exposes a regression.

- [ ] **Step 1: Run backend tests**

Run: `.\.venv\Scripts\python -m pytest backend/tests -q`

Expected: PASS.

- [ ] **Step 2: Run frontend tests and build**

Run from `apps/desktop`:
- `$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test`
- `$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm run build`

Expected: PASS.

- [ ] **Step 3: Run Tauri shell check**

Run: `cargo check --locked` from `apps/desktop/src-tauri`

Expected: PASS.

- [ ] **Step 4: Commit**

Commit message: `feat: add paper tags and favorites`
