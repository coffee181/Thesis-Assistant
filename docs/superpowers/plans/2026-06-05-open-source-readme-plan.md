# Open Source README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the README into a polished open-source project page with real screenshots and clear user/developer guidance.

**Architecture:** Keep this as a docs-only change plus image assets. Generate screenshots from the real local app using an ignored demo library; commit only README, screenshot PNGs, and the spec/plan docs.

**Tech Stack:** Markdown, PowerShell, FastAPI/Uvicorn, Vite/React, Microsoft Edge headless screenshot capture.

---

### Task 1: Commit README Design Documents

**Files:**
- Create: `docs/superpowers/specs/2026-06-05-open-source-readme-design.md`
- Create: `docs/superpowers/plans/2026-06-05-open-source-readme-plan.md`

- [ ] **Step 1: Verify docs are tracked candidates**

Run:

```powershell
git status --short
```

Expected: only the two new docs are listed.

- [ ] **Step 2: Commit docs**

Run:

```powershell
git add docs/superpowers/specs/2026-06-05-open-source-readme-design.md docs/superpowers/plans/2026-06-05-open-source-readme-plan.md
git commit -m "docs: design open source readme"
```

Expected: commit succeeds.

### Task 2: Generate Real Screenshots

**Files:**
- Create: `docs/assets/screenshots/workbench.png`
- Create: `docs/assets/screenshots/reader-assistant.png`

- [ ] **Step 1: Start backend with ignored demo library**

Use `KA_LIBRARY_DIR=F:\knowledge-agent\.local-library\readme-demo` and start the backend on `127.0.0.1:8765`.

- [ ] **Step 2: Import demo PDF through API**

Run:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/imports/pdf" -Method Post -ContentType "application/json" -Body (@{source_path="F:\knowledge-agent\2301.12652v4.pdf"} | ConvertTo-Json)
```

Expected: import succeeds.

- [ ] **Step 3: Start Vite frontend**

Run from `apps/desktop`:

```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

- [ ] **Step 4: Capture screenshots**

Use Microsoft Edge headless to open `http://127.0.0.1:5173`, wait for data, capture the workbench screenshot, click the first paper, and capture the reader/assistant screenshot.

- [ ] **Step 5: Inspect screenshots**

Open the PNGs and confirm they are non-empty and show the real application.

### Task 3: Rewrite README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace development-log structure**

Rewrite README with the approved Hybrid structure:

- Hero section with badges and screenshot.
- Why, screenshots, features, install, quick start, privacy, model settings, development, release, tests, roadmap.

- [ ] **Step 2: Confirm screenshot links**

Run:

```powershell
Select-String -Path README.md -Pattern "docs/assets/screenshots"
Test-Path docs/assets/screenshots/workbench.png
Test-Path docs/assets/screenshots/reader-assistant.png
```

Expected: README references existing assets.

### Task 4: Verify and Commit

**Files:**
- Modify: `README.md`
- Create: `docs/assets/screenshots/*.png`

- [ ] **Step 1: Run docs hygiene checks**

Run:

```powershell
git diff --check
git grep -n -E 'sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----' -- README.md docs backend apps scripts
git ls-files | Select-String -Pattern '2301.12652v4.pdf|src-tauri/binaries|target/release/bundle|\.venv|node_modules|KnowledgeAgentLibrary|sk-[A-Za-z0-9]{20,}'
```

Expected: no whitespace errors, no real secret matches, no generated artifacts tracked.

- [ ] **Step 2: Run focused frontend build**

Run from `apps/desktop`:

```powershell
npm run build
```

Expected: build passes.

- [ ] **Step 3: Commit README assets**

Run:

```powershell
git add README.md docs/assets/screenshots/workbench.png docs/assets/screenshots/reader-assistant.png docs/superpowers/plans/2026-06-05-open-source-readme-plan.md
git commit -m "docs: polish open source readme"
```

Expected: commit succeeds.

### Task 5: Push

- [ ] **Step 1: Push master**

Run:

```powershell
git push
```

Expected: `master` updates on `origin`.
