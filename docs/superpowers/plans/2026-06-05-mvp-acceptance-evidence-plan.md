# MVP Acceptance Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record the evidence that the Knowledge Agent MVP acceptance criteria are implemented and freshly verified.

**Architecture:** This is a documentation and verification slice only. It adds an acceptance matrix that maps the product spec criteria to concrete implementation files, automated tests, and manual smoke evidence; it does not change runtime behavior.

**Tech Stack:** Markdown, pytest, Vitest, Vite build, Cargo, real-PDF smoke script.

---

### Task 1: Acceptance Evidence Document

**Files:**
- Create: `docs/superpowers/mvp-acceptance.md`
- Read: `docs/superpowers/specs/2026-06-05-knowledge-agent-design.md`
- Read: `README.md`
- Read: `backend/tests/test_api.py`
- Read: `backend/tests/test_import_service.py`
- Read: `backend/tests/test_assistant.py`
- Read: `backend/tests/test_providers.py`
- Read: `backend/tests/test_smoke_real_pdf.py`
- Read: `apps/desktop/src/App.test.tsx`

- [x] **Step 1: Write the acceptance matrix**

Create `docs/superpowers/mvp-acceptance.md` with one row for each of the 10 MVP Acceptance Criteria from the spec. Each row must include:
- Criterion number and short text.
- Product evidence in implementation files.
- Automated test evidence.
- Status as `Accepted`, `Accepted with caveat`, or `Not accepted`.

- [x] **Step 2: Record non-blocking baseline gaps**

In the same file, add a short section for baseline implementation decisions that are not fully met but do not block the 10 MVP criteria. Include:
- PDF.js wrapper is not used; the MVP uses a browser PDF iframe plus extracted text layer.
- Chroma is not used; the MVP uses a lightweight persistent local vector index.
- PyInstaller sidecar packaging is not implemented; Tauri can start the backend in development and supports an override command.

### Task 2: Fresh Verification Snapshot

**Files:**
- Modify: `docs/superpowers/mvp-acceptance.md`

- [x] **Step 1: Run backend tests**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
```

Expected: exit 0.

- [x] **Step 2: Run frontend tests**

Run from `apps/desktop`:

```powershell
npm test
```

Expected: exit 0.

- [x] **Step 3: Run frontend build**

Run from `apps/desktop`:

```powershell
npm run build
```

Expected: exit 0.

- [x] **Step 4: Run Tauri shell check**

Run from `apps/desktop/src-tauri`:

```powershell
cargo check --locked
```

Expected: exit 0.

- [x] **Step 5: Run real PDF smoke test**

Run from the repository root with secrets supplied only through environment variables:

```powershell
.\.venv\Scripts\python .\scripts\smoke_real_pdf.py
```

Required environment:
- `KA_SMOKE_PDF=F:\knowledge-agent\2301.12652v4.pdf`
- `KA_SMOKE_BASE_URL=https://keungliang.dpdns.org/`
- `KA_SMOKE_MODEL=glm-5.1`
- `KA_SMOKE_API_KEY=<secret>`
- `KA_SMOKE_PROXY_URL=http://127.0.0.1:7897`

Expected: exit 0 with positive page and citation counts.

- [x] **Step 6: Update verification snapshot**

Record the commands, date, and observed pass counts in `docs/superpowers/mvp-acceptance.md`. Do not record API keys or raw model responses.

### Task 3: Hygiene and Commit

**Files:**
- Modify: `docs/superpowers/plans/2026-06-05-mvp-acceptance-evidence-plan.md`
- Modify: `docs/superpowers/mvp-acceptance.md`

- [x] **Step 1: Run diff whitespace check**

Run:

```powershell
git diff --check
```

Expected: no whitespace errors.

- [x] **Step 2: Run secret scan**

Run:

```powershell
git grep -n "sk-" -- README.md docs backend apps scripts
```

Expected: no matches containing a real API key.

- [x] **Step 3: Commit**

Run:

```powershell
git add docs/superpowers/plans/2026-06-05-mvp-acceptance-evidence-plan.md docs/superpowers/mvp-acceptance.md
git commit -m "docs: record mvp acceptance evidence"
```
