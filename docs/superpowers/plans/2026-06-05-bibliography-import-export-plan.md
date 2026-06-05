# Bibliography Import and Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add BibTeX and RIS import/export so the local library can manage literature metadata, not only PDFs.

**Architecture:** Extend the existing `papers` table with bibliographic metadata columns and add focused parser/exporter helpers for BibTeX and RIS. Keep the first version synchronous and path-based like the existing PDF import. The desktop app exposes a compact path import form and export text preview, while PDF import and reader behavior continue unchanged.

**Tech Stack:** Python 3.13, FastAPI, SQLite, pytest, React, TypeScript, Vitest, Testing Library.

---

## Scope

This plan implements:

- Paper metadata columns: authors, venue, abstract, citation key, arXiv ID, entry type.
- BibTeX parser for common `@article`, `@inproceedings`, `@misc`, and related entries.
- RIS parser for common `TY`, `TI`, `AU`, `PY`, `DO`, `JO`/`JF`/`T2`, `AB`, and `ID` tags.
- Bibliography import by local path with DOI/citation-key/title deduplication.
- BibTeX and RIS export for the local library.
- Desktop controls for bibliography import and export preview.

This plan does not implement Zotero sync, CSL formatting, metadata lookup, attachment matching, PDF download, or full BibTeX macro/string expansion.

## File Structure

Create or modify:

```text
backend/
  src/knowledge_agent/
    bibliography.py
    db.py
    main.py
    models.py
    repositories.py
    schemas.py
  tests/
    test_api.py
    test_bibliography.py
    test_database.py
apps/
  desktop/
    src/
      App.test.tsx
      App.tsx
      api.ts
      styles.css
docs/
  superpowers/plans/2026-06-05-bibliography-import-export-plan.md
```

Responsibilities:

- `backend/src/knowledge_agent/bibliography.py`: Parse BibTeX/RIS records and export papers back to BibTeX/RIS.
- `backend/src/knowledge_agent/db.py`: Add paper metadata columns and indexes.
- `backend/src/knowledge_agent/models.py`: Extend `Paper` and add bibliography record/result models.
- `backend/src/knowledge_agent/repositories.py`: Add bibliographic upsert and lookup behavior.
- `backend/src/knowledge_agent/main.py`: Add bibliography import/export API endpoints.
- `apps/desktop/src/api.ts`: Add bibliography import/export client calls and types.
- `apps/desktop/src/App.tsx`: Add bibliography import form and export preview.

## Task 1: Paper Metadata Persistence

**Files:**
- Modify: `backend/src/knowledge_agent/db.py`
- Modify: `backend/src/knowledge_agent/models.py`
- Modify: `backend/src/knowledge_agent/repositories.py`
- Modify: `backend/tests/test_database.py`

- [ ] **Step 1: Write failing metadata repository tests**

Add tests proving:

- `init_db` creates paper columns `authors`, `venue`, `abstract`, `citation_key`, `arxiv_id`, and `entry_type`.
- `PapersRepository.create` can persist these fields.
- `PapersRepository.upsert_metadata` updates an existing DOI match instead of creating a duplicate.
- `PapersRepository.upsert_metadata` deduplicates by citation key when DOI is missing.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py -q
```

Expected: FAIL because the metadata columns and upsert method do not exist.

- [ ] **Step 2: Implement metadata persistence**

Add nullable columns to `papers` with migration guards:

- `authors text`
- `venue text`
- `abstract text`
- `citation_key text`
- `arxiv_id text`
- `entry_type text`

Add a unique partial index on `citation_key where citation_key is not null`.

Extend `Paper` and `PapersRepository.create`. Add `PapersRepository.upsert_metadata(record)` and use DOI, citation key, then normalized title/year matching.

- [ ] **Step 3: Verify metadata tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add backend/src/knowledge_agent/db.py backend/src/knowledge_agent/models.py backend/src/knowledge_agent/repositories.py backend/tests/test_database.py
git commit -m "feat: store bibliography metadata"
```

## Task 2: BibTeX and RIS Parser/Exporter

**Files:**
- Create: `backend/src/knowledge_agent/bibliography.py`
- Create: `backend/tests/test_bibliography.py`

- [ ] **Step 1: Write failing parser/exporter tests**

Add tests proving:

- BibTeX records parse citation key, title, authors, year, DOI, venue, abstract, and entry type.
- RIS records parse title, repeated authors, year, DOI, venue, abstract, and ID.
- BibTeX export includes stable citation keys and escaped field values.
- RIS export includes `TY`, `ID`, `TI`, repeated `AU`, `PY`, `DO`, `JO`, `AB`, and `ER`.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_bibliography.py -q
```

Expected: FAIL because `knowledge_agent.bibliography` does not exist.

- [ ] **Step 2: Implement parser/exporter helpers**

Implement:

- `parse_bibtex(content: str) -> list[BibliographyRecord]`
- `parse_ris(content: str) -> list[BibliographyRecord]`
- `parse_bibliography(content: str, format_name: str) -> list[BibliographyRecord]`
- `export_bibtex(papers: list[Paper]) -> str`
- `export_ris(papers: list[Paper]) -> str`

- [ ] **Step 3: Verify parser/exporter tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_bibliography.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add backend/src/knowledge_agent/bibliography.py backend/tests/test_bibliography.py
git commit -m "feat: parse and export bibliography formats"
```

## Task 3: Bibliography Import and Export APIs

**Files:**
- Modify: `backend/src/knowledge_agent/schemas.py`
- Modify: `backend/src/knowledge_agent/main.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Add tests proving:

- `POST /api/imports/bibliography` imports a `.bib` file and listed papers include metadata.
- Re-importing a record with the same DOI updates metadata and reports `updated_count`.
- `GET /api/exports/bibliography?format=bibtex` returns BibTeX text.
- `GET /api/exports/bibliography?format=ris` returns RIS text.
- Missing source path returns 404.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py -q
```

Expected: FAIL because the bibliography endpoints are missing.

- [ ] **Step 2: Implement schemas and endpoints**

Add:

- `ImportBibliographyRequest`
- `ImportBibliographyResponse`
- `ExportBibliographyResponse`

Implement path format detection from `.bib` and `.ris` when request format is omitted. Return export payload as JSON `{format, content}` for easy desktop preview.

- [ ] **Step 3: Verify API tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add backend/src/knowledge_agent/schemas.py backend/src/knowledge_agent/main.py backend/tests/test_api.py
git commit -m "feat: expose bibliography import export api"
```

## Task 4: Desktop Bibliography Workflow

**Files:**
- Modify: `apps/desktop/src/api.ts`
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Write failing frontend tests**

Add tests proving:

- The user can import a bibliography file path and the library refreshes.
- Paper rows display author/year metadata when present.
- The user can request BibTeX export and see export content in a preview area.

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
```

Expected: FAIL because the desktop bibliography controls do not exist.

- [ ] **Step 2: Implement API client calls**

Add:

- `importBibliography(sourcePath, format?)`
- `exportBibliography(format)`
- extended `Paper` metadata fields.

- [ ] **Step 3: Implement desktop UI**

Add to the left library pane:

- Bibliography source path input.
- Format selector with auto/BibTeX/RIS.
- Import bibliography button.
- Export BibTeX and Export RIS buttons.
- Export preview textarea.

Update paper rows to show authors and year when present.

- [ ] **Step 4: Verify frontend tests pass**

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add apps/desktop/src/api.ts apps/desktop/src/App.test.tsx apps/desktop/src/App.tsx apps/desktop/src/styles.css
git commit -m "feat: add desktop bibliography workflow"
```

## Final Verification

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm run build
```

Expected: all commands exit 0.

