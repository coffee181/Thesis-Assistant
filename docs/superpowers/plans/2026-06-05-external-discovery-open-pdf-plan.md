# External Discovery and Open PDF Download Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the desktop app search external literature sources, download open-access PDFs to a pending area, and import confirmed downloads into the managed local library.

**Architecture:** Add a small discovery boundary that normalizes provider responses into one candidate model, caches candidates in SQLite, and keeps network I/O injectable for tests. Downloaded PDFs first land under `downloads/pending/`; a separate confirmation endpoint imports the pending PDF through the existing managed PDF import path and applies candidate metadata to the imported paper.

**Tech Stack:** Python 3.13, FastAPI, SQLite, httpx, pytest, React, TypeScript, Vitest, Testing Library.

---

## Scope

This plan implements:

- External search by keyword/title, DOI, and arXiv ID/URL.
- Candidate normalization from OpenAlex, arXiv API, and Unpaywall-style payloads.
- Candidate deduplication by DOI, arXiv ID, then source/external ID.
- Cached `search_results` records in SQLite.
- Open PDF download to `downloads/pending`.
- User-confirmed import from a pending PDF into the managed library.
- Desktop controls for external discovery, open-PDF download, and confirmed import.

This plan does not implement Semantic Scholar, background job progress, proxy settings, retries beyond ordinary HTTP errors, vector search, folder PDF import, notes, or highlights.

## File Structure

Create or modify:

```text
backend/
  src/knowledge_agent/
    db.py
    discovery.py
    import_service.py
    main.py
    models.py
    repositories.py
    schemas.py
  tests/
    test_api.py
    test_database.py
    test_discovery.py
    test_import_service.py
apps/
  desktop/
    src/
      App.test.tsx
      App.tsx
      api.ts
      styles.css
docs/
  superpowers/plans/2026-06-05-external-discovery-open-pdf-plan.md
```

Responsibilities:

- `backend/src/knowledge_agent/discovery.py`: Query classification, provider response normalization, candidate merge, HTTP search client, and pending PDF download helper.
- `backend/src/knowledge_agent/db.py`: Create `search_results` cache table.
- `backend/src/knowledge_agent/models.py`: Add `DiscoveryCandidate` and `SearchResultRecord`.
- `backend/src/knowledge_agent/repositories.py`: Add `SearchResultsRepository` and paper metadata update support for confirmed imports.
- `backend/src/knowledge_agent/import_service.py`: Accept optional bibliographic metadata when importing a PDF.
- `backend/src/knowledge_agent/main.py`: Add external search, pending download, and confirmed import endpoints.
- `apps/desktop/src/api.ts`: Add typed external discovery and pending import API calls.
- `apps/desktop/src/App.tsx`: Add external discovery form, result rows, download buttons, and confirm import buttons.

## Task 1: Search Result Cache Persistence

**Files:**
- Modify: `backend/src/knowledge_agent/db.py`
- Modify: `backend/src/knowledge_agent/models.py`
- Modify: `backend/src/knowledge_agent/repositories.py`
- Modify: `backend/tests/test_database.py`

- [ ] **Step 1: Write failing search result repository tests**

Add tests proving:

- `init_db` creates `search_results`.
- `SearchResultsRepository.replace_for_query` stores normalized discovery candidates.
- Replacing the same query removes old rows for that query.
- Duplicate source/external ID records update instead of creating duplicates.

Use this shape in `backend/tests/test_database.py`:

```python
from knowledge_agent.models import DiscoveryCandidate
from knowledge_agent.repositories import SearchResultsRepository


def test_search_results_repository_replaces_query_results(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        repository = SearchResultsRepository(conn)
        first = repository.replace_for_query(
            "local rag",
            [
                DiscoveryCandidate(
                    source="openalex",
                    external_id="W123",
                    title="Local RAG",
                    authors="Jane Doe",
                    year=2024,
                    doi="10.123/local",
                    venue="Journal of Local Research",
                    abstract="Traceable assistants.",
                    arxiv_id=None,
                    pdf_url="https://example.test/local.pdf",
                    landing_url="https://example.test/local",
                )
            ],
        )
        second = repository.replace_for_query(
            "local rag",
            [
                DiscoveryCandidate(
                    source="arxiv",
                    external_id="2401.12345",
                    title="ArXiv Local RAG",
                    authors="Jane Doe and John Smith",
                    year=2024,
                    doi=None,
                    venue="arXiv",
                    abstract=None,
                    arxiv_id="2401.12345",
                    pdf_url="https://arxiv.org/pdf/2401.12345",
                    landing_url="https://arxiv.org/abs/2401.12345",
                )
            ],
        )

    assert [record.title for record in first] == ["Local RAG"]
    assert [record.title for record in second] == ["ArXiv Local RAG"]
    assert second[0].query == "local rag"
    assert second[0].pdf_url == "https://arxiv.org/pdf/2401.12345"
```

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py -q
```

Expected: FAIL because `DiscoveryCandidate` and `SearchResultsRepository` do not exist.

- [ ] **Step 2: Implement search result persistence**

Add this dataclass to `backend/src/knowledge_agent/models.py`:

```python
@dataclass(frozen=True)
class DiscoveryCandidate:
    source: str
    external_id: str
    title: str
    authors: str | None
    year: int | None
    doi: str | None
    venue: str | None
    abstract: str | None
    arxiv_id: str | None
    pdf_url: str | None
    landing_url: str | None


@dataclass(frozen=True)
class SearchResultRecord:
    id: int
    query: str
    source: str
    external_id: str
    title: str
    authors: str | None
    year: int | None
    doi: str | None
    venue: str | None
    abstract: str | None
    arxiv_id: str | None
    pdf_url: str | None
    landing_url: str | None
    created_at: str
```

Add this table to `init_db`:

```sql
create table if not exists search_results (
    id integer primary key autoincrement,
    query text not null,
    source text not null,
    external_id text not null,
    title text not null,
    authors text,
    year integer,
    doi text,
    venue text,
    abstract text,
    arxiv_id text,
    pdf_url text,
    landing_url text,
    created_at text not null default current_timestamp,
    unique(source, external_id)
);

create index if not exists idx_search_results_query
on search_results(query);
```

Add `SearchResultsRepository` with:

```python
def replace_for_query(
    self,
    query: str,
    candidates: list[DiscoveryCandidate],
) -> list[SearchResultRecord]:
    ...

def list_for_query(self, query: str) -> list[SearchResultRecord]:
    ...

def get(self, result_id: int) -> SearchResultRecord:
    ...
```

`replace_for_query` should delete rows for the query, upsert each candidate by `(source, external_id)`, then return `list_for_query(query)`.

- [ ] **Step 3: Verify search result persistence tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add backend/src/knowledge_agent/db.py backend/src/knowledge_agent/models.py backend/src/knowledge_agent/repositories.py backend/tests/test_database.py
git commit -m "feat: cache external search results"
```

## Task 2: Discovery Normalization and HTTP Client

**Files:**
- Create: `backend/src/knowledge_agent/discovery.py`
- Create: `backend/tests/test_discovery.py`

- [ ] **Step 1: Write failing discovery tests**

Add tests proving:

- DOI and arXiv URL queries are classified correctly.
- OpenAlex work JSON normalizes title, authors, year, DOI, venue, landing URL, and best open PDF URL.
- arXiv Atom XML normalizes title, authors, year, arXiv ID, abstract, landing URL, and PDF URL.
- Unpaywall JSON normalizes DOI and best OA location PDF URL.
- Merging candidates deduplicates by DOI and keeps a PDF URL when only one duplicate has it.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_discovery.py -q
```

Expected: FAIL because `knowledge_agent.discovery` does not exist.

- [ ] **Step 2: Implement discovery helpers**

Implement in `backend/src/knowledge_agent/discovery.py`:

```python
def classify_query(query: str) -> tuple[str, str]:
    ...

def normalize_openalex_work(work: dict[str, object]) -> DiscoveryCandidate:
    ...

def normalize_arxiv_feed(content: str) -> list[DiscoveryCandidate]:
    ...

def normalize_unpaywall_record(record: dict[str, object]) -> DiscoveryCandidate:
    ...

def merge_candidates(candidates: list[DiscoveryCandidate]) -> list[DiscoveryCandidate]:
    ...
```

Use DOI, arXiv ID, then `source:external_id` as merge keys. Do not call real network in these functions.

- [ ] **Step 3: Add injectable HTTP discovery client**

Add:

```python
class ExternalDiscoveryClient:
    def __init__(self, http_client: httpx.Client | None = None) -> None:
        ...

    def search(self, query: str, limit: int = 10) -> list[DiscoveryCandidate]:
        ...
```

The client should:

- Use OpenAlex `/works?search=...` for keyword/title/arXiv queries and `/works/doi:{doi}` for DOI queries.
- Use arXiv Atom API for keyword/title/arXiv queries.
- Use Unpaywall only when `classify_query` returns DOI.
- Catch provider HTTP/parsing errors per provider and return candidates from other providers.

- [ ] **Step 4: Verify discovery tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_discovery.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/src/knowledge_agent/discovery.py backend/tests/test_discovery.py
git commit -m "feat: discover open access paper candidates"
```

## Task 3: Open PDF Download and Confirmed Import APIs

**Files:**
- Modify: `backend/src/knowledge_agent/import_service.py`
- Modify: `backend/src/knowledge_agent/main.py`
- Modify: `backend/src/knowledge_agent/repositories.py`
- Modify: `backend/src/knowledge_agent/schemas.py`
- Modify: `backend/tests/test_api.py`
- Modify: `backend/tests/test_import_service.py`

- [ ] **Step 1: Write failing import-service metadata tests**

Add tests proving `import_pdf(..., metadata=BibliographyRecord(...))` creates the paper with metadata, and duplicate hash imports return the existing document while updating missing metadata.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_import_service.py -q
```

Expected: FAIL because `import_pdf` does not accept `metadata`.

- [ ] **Step 2: Implement metadata-aware PDF import**

Change `import_pdf` signature to:

```python
def import_pdf(
    conn: sqlite3.Connection,
    library_root: Path,
    source_path: Path,
    metadata: BibliographyRecord | None = None,
) -> ImportResult:
    ...
```

When `metadata` is present, create the paper using metadata fields instead of the source filename. If a duplicate document hash already exists, update that existing paper with the metadata and return `imported=False`.

Add a repository helper:

```python
def update_metadata(self, paper_id: int, record: BibliographyRecord) -> Paper:
    ...
```

- [ ] **Step 3: Write failing API tests**

Add tests proving:

- `GET /api/search/external?q=local rag` returns cached candidate records using an injected fake discovery client.
- `POST /api/downloads/open-pdf` downloads a PDF from a search result `pdf_url` into `downloads/pending`.
- `POST /api/imports/pending-download` imports that pending PDF, applies candidate metadata, and refreshes `/api/papers`.
- Search result without `pdf_url` returns 400 for download.
- Missing search result returns 404.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py -q
```

Expected: FAIL because the external search and download endpoints are missing.

- [ ] **Step 4: Implement schemas and endpoints**

Add schemas:

```python
class ExternalSearchResponse(BaseModel):
    query: str
    results: list[SearchResultResponse]

class OpenPdfDownloadRequest(BaseModel):
    search_result_id: int

class OpenPdfDownloadResponse(BaseModel):
    pending_path: str
    result: SearchResultResponse

class ImportPendingDownloadRequest(BaseModel):
    search_result_id: int
    pending_path: str = Field(min_length=1)
```

Add endpoints:

- `GET /api/search/external?q=<query>`
- `POST /api/downloads/open-pdf`
- `POST /api/imports/pending-download`

Use `create_app(..., discovery_client=None, pdf_downloader=None)` injection so tests do not touch the network. Pending downloads must stay under `config.library_dir / "downloads" / "pending"` after path resolution.

- [ ] **Step 5: Verify API tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_import_service.py backend/tests/test_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/src/knowledge_agent/import_service.py backend/src/knowledge_agent/main.py backend/src/knowledge_agent/repositories.py backend/src/knowledge_agent/schemas.py backend/tests/test_api.py backend/tests/test_import_service.py
git commit -m "feat: download and import open access pdfs"
```

## Task 4: Desktop External Discovery Workflow

**Files:**
- Modify: `apps/desktop/src/api.ts`
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Write failing frontend tests**

Add tests proving:

- The user can search external papers and see title, authors/year, source, and open PDF availability.
- A result with `pdf_url` can be downloaded to pending and then confirmed into the library.
- A result without `pdf_url` shows `Needs access` and has no download action.

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
```

Expected: FAIL because external discovery UI and API calls do not exist.

- [ ] **Step 2: Implement API client calls**

Add types and functions in `apps/desktop/src/api.ts`:

```ts
export type SearchResultRecord = {
  id: number;
  query: string;
  source: string;
  external_id: string;
  title: string;
  authors: string | null;
  year: number | null;
  doi: string | null;
  venue: string | null;
  abstract: string | null;
  arxiv_id: string | null;
  pdf_url: string | null;
  landing_url: string | null;
  created_at: string;
};

export async function searchExternal(query: string): Promise<ExternalSearchResponse>;
export async function downloadOpenPdf(searchResultId: number): Promise<OpenPdfDownloadResponse>;
export async function importPendingDownload(searchResultId: number, pendingPath: string): Promise<void>;
```

- [ ] **Step 3: Implement desktop UI**

Add a compact external discovery section in the left pane:

- Query input labelled `External search`.
- `Search external` button.
- Results list below local search results or in its own section.
- Each result shows title, `authors · year`, source, DOI/arXiv when present, and either `Open PDF available` or `Needs access`.
- Results with a PDF URL show `Download PDF`.
- Downloaded results show `Confirm import`.

After confirm import, refresh the library and show `Downloaded paper imported`.

- [ ] **Step 4: Verify frontend tests pass**

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add apps/desktop/src/api.ts apps/desktop/src/App.test.tsx apps/desktop/src/App.tsx apps/desktop/src/styles.css
git commit -m "feat: add desktop external discovery workflow"
```

## Final Verification

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm run build
```

Expected: all commands exit 0.

## Self-Review Notes

- Spec coverage: Covers MVP acceptance criteria 4 and 5, plus the `search_results` table from the data model. Folder import, selected-text translation, notes, highlights, and packaging remain separate plans.
- Placeholder scan: No unfinished placeholder markers or unspecified test commands remain.
- Type consistency: Candidate fields are shared across `DiscoveryCandidate`, `SearchResultRecord`, API schemas, and desktop API types.
