# Background Jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add observable folder-import jobs with progress, failure details, and retry support.

**Architecture:** Store job state in SQLite so long-running work is visible and recoverable. Keep the existing synchronous single-PDF import path unchanged; change folder import to create a job and run the import work through a job runner that updates progress after each PDF. The desktop app shows a compact jobs panel and lets users retry failed folder-import jobs.

**Tech Stack:** FastAPI `BackgroundTasks`, SQLite, pytest, React, TypeScript, Vitest.

---

### Task 1: Backend Job Storage and Runner

**Files:**
- Modify: `backend/src/knowledge_agent/db.py`
- Modify: `backend/src/knowledge_agent/models.py`
- Modify: `backend/src/knowledge_agent/repositories.py`
- Create: `backend/src/knowledge_agent/job_service.py`
- Test: `backend/tests/test_database.py`
- Test: `backend/tests/test_import_service.py`

- [ ] **Step 1: Write failing repository tests**

Add tests proving:
- `init_db()` creates a `jobs` table.
- `JobsRepository.create()` stores `kind`, `status`, `source_path`, counters, and timestamps.
- `JobsRepository.start()`, `update_progress()`, `complete()`, and `fail()` update the record.
- `JobsRepository.list_recent()` orders newest jobs first.

- [ ] **Step 2: Run repository tests to verify RED**

Run: `.\.venv\Scripts\python -m pytest backend/tests/test_database.py::test_jobs_repository_tracks_state_transitions -q`

Expected: FAIL because `JobsRepository` and the `jobs` table do not exist.

- [ ] **Step 3: Write failing runner tests**

Add tests proving:
- `run_folder_import_job(conn, library_root, job_id, source_dir)` marks the job `running`, then `succeeded`.
- Progress counters match discovered/imported/skipped/failed PDFs.
- Per-file failures are stored in `result_json`.
- A non-folder source marks the job `failed` and stores the error.

- [ ] **Step 4: Run runner tests to verify RED**

Run: `.\.venv\Scripts\python -m pytest backend/tests/test_import_service.py::test_folder_import_job_updates_progress backend/tests/test_import_service.py::test_folder_import_job_records_failure -q`

Expected: FAIL because the runner does not exist.

- [ ] **Step 5: Implement backend storage and runner**

Implement:
- `Job` dataclass with `id`, `kind`, `status`, `source_path`, `description`, `total_items`, `processed_items`, `succeeded_items`, `failed_items`, `error`, `result_json`, `created_at`, `updated_at`.
- `jobs` table with `status` values stored as text.
- `JobsRepository` methods: `create()`, `get()`, `list_recent()`, `start()`, `update_progress()`, `complete()`, `fail()`.
- `run_folder_import_job()` that scans PDFs, imports each with existing `import_pdf()`, updates counters after each file, and stores the same summary shape as the old folder import response in `result_json`.

- [ ] **Step 6: Run backend storage and runner tests to verify GREEN**

Run: `.\.venv\Scripts\python -m pytest backend/tests/test_database.py::test_jobs_repository_tracks_state_transitions backend/tests/test_import_service.py::test_folder_import_job_updates_progress backend/tests/test_import_service.py::test_folder_import_job_records_failure -q`

Expected: PASS.

### Task 2: Backend Job API

**Files:**
- Modify: `backend/src/knowledge_agent/main.py`
- Modify: `backend/src/knowledge_agent/schemas.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Add tests proving:
- `POST /api/imports/folder` returns `202` with a job response instead of the old folder summary.
- `GET /api/jobs` returns recent jobs.
- `GET /api/jobs/{job_id}` returns job detail.
- `POST /api/jobs/{job_id}/retry` creates a new queued job for failed `folder_import` jobs using the original `source_path`.
- Retrying a succeeded job returns `400`.

- [ ] **Step 2: Run API tests to verify RED**

Run: `.\.venv\Scripts\python -m pytest backend/tests/test_api.py::test_folder_import_endpoint_creates_observable_job backend/tests/test_api.py::test_failed_folder_import_job_can_be_retried -q`

Expected: FAIL because job schemas/endpoints are missing and folder import still returns the old summary.

- [ ] **Step 3: Implement API support**

Implement:
- `JobResponse`, `JobsResponse`, and `RetryJobResponse` schemas.
- `POST /api/imports/folder` that validates the folder, creates a `folder_import` job, schedules the runner through `BackgroundTasks`, and returns `202`.
- `GET /api/jobs` and `GET /api/jobs/{job_id}`.
- `POST /api/jobs/{job_id}/retry` that only accepts failed `folder_import` jobs and schedules a new job with the same `source_path`.

- [ ] **Step 4: Run API tests to verify GREEN**

Run: `.\.venv\Scripts\python -m pytest backend/tests/test_api.py::test_folder_import_endpoint_creates_observable_job backend/tests/test_api.py::test_failed_folder_import_job_can_be_retried -q`

Expected: PASS.

### Task 3: Desktop Job Panel

**Files:**
- Modify: `apps/desktop/src/api.ts`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Write failing desktop tests**

Add tests proving:
- Submitting a folder import calls `POST /api/imports/folder`, displays the returned job, refreshes jobs, and no longer expects immediate import counts.
- The jobs panel displays status and progress counters.
- Clicking retry on a failed job calls `POST /api/jobs/{job_id}/retry` and refreshes jobs.

- [ ] **Step 2: Run desktop tests to verify RED**

Run: `$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test -- -t "job panel"`

Expected: FAIL because the API helpers and UI are missing.

- [ ] **Step 3: Implement desktop support**

Implement:
- `Job`, `JobsResponse`, `importFolder()` returning `Job`, `listJobs()`, `retryJob()`.
- App state for recent jobs.
- Initial load includes `listJobs()`.
- Folder import message becomes `Folder import queued`.
- A compact jobs panel in the left sidebar showing status, processed/total counters, failure text, and retry buttons for failed jobs.

- [ ] **Step 4: Run desktop tests to verify GREEN**

Run: `$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test -- -t "job panel"`

Expected: PASS.

### Task 4: Verification and Commit

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

Commit message: `feat: add observable import jobs`
