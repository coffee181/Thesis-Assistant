# Local Metadata Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let local library search find literature records by metadata even when the paper has no imported PDF or extracted chunks.

**Architecture:** Keep the existing `/api/search/local` endpoint and search UI, but extend local search results so document/page fields may be `null` for metadata-only hits. The backend returns full-text chunk hits first and fills remaining slots with paper metadata matches from title, authors, DOI, venue, abstract, citation key, and arXiv ID. The frontend displays metadata-only hits without pretending there is a PDF page to open.

**Tech Stack:** Python 3.13, SQLite, FastAPI, Pydantic, React, Vitest, pytest.

---

### Task 1: Backend Metadata Search

**Files:**
- Modify: `backend/src/knowledge_agent/models.py`
- Modify: `backend/src/knowledge_agent/schemas.py`
- Modify: `backend/src/knowledge_agent/repositories.py`
- Test: `backend/tests/test_database.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing repository test**

Add this test to `backend/tests/test_database.py` after `test_chunks_replace_list_and_search`:

```python
def test_local_search_finds_metadata_only_papers(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        papers = PapersRepository(conn)
        chunks = ChunksRepository(conn)
        paper = papers.upsert_metadata(
            BibliographyRecord(
                citation_key="doe2024traceable",
                title="Traceable Literature Assistants",
                authors="Jane Doe and John Smith",
                year=2024,
                doi="10.1234/traceable",
                venue="Journal of Research Tools",
                abstract="A study of local knowledge-base research assistants.",
                arxiv_id="2401.12345",
                entry_type="article",
            )
        )

        hits = chunks.search("10.1234/traceable")

    assert len(hits) == 1
    assert hits[0].paper_id == paper.id
    assert hits[0].title == "Traceable Literature Assistants"
    assert hits[0].document_id is None
    assert hits[0].chunk_id is None
    assert hits[0].page_number is None
    assert "10.1234/traceable" in hits[0].snippet
```

- [ ] **Step 2: Run repository test to verify RED**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py::test_local_search_finds_metadata_only_papers -q
```

Expected: FAIL because current search only queries `chunks_fts`.

- [ ] **Step 3: Implement metadata search**

Update `SearchHit` in `backend/src/knowledge_agent/models.py` and `SearchHitResponse` in `backend/src/knowledge_agent/schemas.py` so `document_id`, `chunk_id`, and `page_number` are `int | None`.

Update `ChunksRepository.search()` to:
- Query chunk FTS as it does today.
- Track paper IDs already returned.
- Query `papers` with `like` across title, authors, DOI, venue, abstract, citation key, and arXiv ID.
- Return metadata hits with `document_id=None`, `chunk_id=None`, `page_number=None`, and a concise snippet built from the matched metadata.
- Preserve chunk hits before metadata hits.

- [ ] **Step 4: Run repository test to verify GREEN**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py::test_local_search_finds_metadata_only_papers -q
```

Expected: PASS.

- [ ] **Step 5: Write failing API test**

Add this test to `backend/tests/test_api.py` near the local search tests:

```python
def test_local_search_returns_metadata_only_hits(tmp_path: Path):
    library_dir = tmp_path / "library"
    bib_path = tmp_path / "library.bib"
    bib_path.write_text(
        """
        @article{doe2024traceable,
          title = {Traceable Literature Assistants},
          author = {Jane Doe and John Smith},
          year = {2024},
          doi = {10.1234/traceable},
          journal = {Journal of Research Tools},
          abstract = {A study of local knowledge-base research assistants.}
        }
        """,
        encoding="utf-8",
    )
    client = TestClient(create_app(library_dir=library_dir))
    client.post(
        "/api/imports/bibliography",
        json={"source_path": str(bib_path), "format": "bibtex"},
    )

    response = client.get("/api/search/local", params={"q": "10.1234/traceable"})

    assert response.status_code == 200
    hit = response.json()["hits"][0]
    assert hit["title"] == "Traceable Literature Assistants"
    assert hit["document_id"] is None
    assert hit["chunk_id"] is None
    assert hit["page_number"] is None
    assert "10.1234/traceable" in hit["snippet"]
```

- [ ] **Step 6: Run API test to verify GREEN**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py::test_local_search_returns_metadata_only_hits -q
```

Expected: PASS.

### Task 2: Desktop Metadata Search Display

**Files:**
- Modify: `apps/desktop/src/api.ts`
- Modify: `apps/desktop/src/App.tsx`
- Test: `apps/desktop/src/App.test.tsx`

- [ ] **Step 1: Write failing UI test**

Add this test near the existing local search UI test:

```typescript
it("displays metadata-only local search hits without page links", async () => {
  fetchMock
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => defaultLibraryStatus,
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ papers: [] }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => defaultProviderSettings,
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => emptyJobsResponse,
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        query: "10.1234/traceable",
        hits: [
          {
            paper_id: 12,
            title: "Traceable Literature Assistants",
            year: 2024,
            doi: "10.1234/traceable",
            document_id: null,
            chunk_id: null,
            page_number: null,
            snippet: "Traceable Literature Assistants. Jane Doe and John Smith. DOI 10.1234/traceable.",
          },
        ],
      }),
    });

  render(<App />);
  await userEvent.type(await screen.findByLabelText("Search library"), "10.1234/traceable");
  await userEvent.click(screen.getByRole("button", { name: "Search" }));

  expect(await screen.findByText("Traceable Literature Assistants")).toBeInTheDocument();
  expect(await screen.findByText("Metadata match")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Open Traceable Literature Assistants page null" })).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run UI test to verify RED**

Run:

```powershell
cd apps\desktop
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test -- --run -t "metadata-only local search"
```

Expected: FAIL because `SearchHit` currently requires page numbers and the UI renders `Page null`.

- [ ] **Step 3: Implement UI display**

Update `SearchHit` in `api.ts` so `document_id`, `chunk_id`, and `page_number` are nullable. In `App.tsx`, render chunk-backed hits as the existing open-paper button. Render metadata-only hits as a non-clickable `article` with:
- paper title
- `Metadata match`
- snippet

- [ ] **Step 4: Run UI test to verify GREEN**

Run:

```powershell
cd apps\desktop
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test -- --run -t "metadata-only local search"
```

Expected: PASS.

### Task 3: Verification and Commit

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

Update the local search bullet to say it searches both extracted PDF pages and paper metadata.

- [ ] **Step 2: Run full verification**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
cd apps\desktop
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm run build
cd apps\desktop\src-tauri
cargo check --locked
cd F:\knowledge-agent
git diff --check
```

Expected: PASS.

- [ ] **Step 3: Commit**

Run:

```powershell
git add README.md backend/src/knowledge_agent/models.py backend/src/knowledge_agent/schemas.py backend/src/knowledge_agent/repositories.py backend/tests/test_database.py backend/tests/test_api.py apps/desktop/src/api.ts apps/desktop/src/App.tsx apps/desktop/src/App.test.tsx docs/superpowers/plans/2026-06-05-local-metadata-search-plan.md
git commit -m "feat: search local paper metadata"
```
