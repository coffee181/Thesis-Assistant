# Crossref and Semantic Scholar Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Crossref and Semantic Scholar as normalized external discovery sources so MVP external search matches the approved design.

**Architecture:** Extend the existing `ExternalDiscoveryClient` provider fan-out without changing API response shapes or persistence. New provider responses normalize into the existing `DiscoveryCandidate` model, then flow through existing DOI/arXiv/source deduplication.

**Tech Stack:** Python 3.13, httpx, pytest, FastAPI backend.

---

## Scope

This plan implements:

- Crossref work normalization.
- Semantic Scholar paper normalization.
- External discovery client calls to Crossref and Semantic Scholar for keyword/title queries.
- Semantic Scholar lookup for DOI and arXiv queries.
- Documentation that external discovery now uses OpenAlex, Crossref, Semantic Scholar, arXiv, and Unpaywall.

This plan does not implement vector search, streaming assistant responses, UI changes, new database fields, provider API keys, or download behavior changes.

## File Structure

Modify:

```text
backend/src/knowledge_agent/discovery.py
backend/tests/test_discovery.py
README.md
docs/superpowers/plans/2026-06-05-crossref-semantic-scholar-discovery-plan.md
```

Responsibilities:

- `backend/src/knowledge_agent/discovery.py`: Add provider constants, normalization helpers, and HTTP client fan-out.
- `backend/tests/test_discovery.py`: Prove normalization and injected-client request behavior without real network calls.
- `README.md`: Reflect the expanded discovery sources.

## Task 1: Crossref and Semantic Scholar Normalization

**Files:**

- Modify: `backend/tests/test_discovery.py`
- Modify: `backend/src/knowledge_agent/discovery.py`

- [ ] **Step 1: Write failing normalization tests**

Add imports:

```python
from knowledge_agent.discovery import (
    normalize_crossref_work,
    normalize_semantic_scholar_paper,
)
```

Add these tests to `backend/tests/test_discovery.py`:

```python
def test_normalize_crossref_work_extracts_metadata_and_links():
    candidate = normalize_crossref_work(
        {
            "DOI": "10.1234/CROSS",
            "title": ["Crossref Local Agents"],
            "author": [
                {"given": "Jane", "family": "Doe"},
                {"name": "Local Consortium"},
            ],
            "published-print": {"date-parts": [[2023, 5, 1]]},
            "container-title": ["Proceedings of Local Research"],
            "abstract": "<jats:p>Traceable discovery from Crossref.</jats:p>",
            "link": [
                {
                    "URL": "https://example.test/crossref.pdf",
                    "content-type": "application/pdf",
                }
            ],
            "URL": "https://doi.org/10.1234/CROSS",
        }
    )

    assert candidate.source == "crossref"
    assert candidate.external_id == "10.1234/cross"
    assert candidate.title == "Crossref Local Agents"
    assert candidate.authors == "Jane Doe and Local Consortium"
    assert candidate.year == 2023
    assert candidate.doi == "10.1234/cross"
    assert candidate.venue == "Proceedings of Local Research"
    assert candidate.abstract == "Traceable discovery from Crossref."
    assert candidate.pdf_url == "https://example.test/crossref.pdf"
    assert candidate.landing_url == "https://doi.org/10.1234/CROSS"


def test_normalize_semantic_scholar_paper_extracts_open_access_pdf():
    candidate = normalize_semantic_scholar_paper(
        {
            "paperId": "S2-123",
            "title": "Semantic Scholar Local Agents",
            "authors": [{"name": "Jane Doe"}, {"name": "John Smith"}],
            "year": 2024,
            "venue": "Local AI",
            "abstract": "Semantic Scholar discovery.",
            "externalIds": {"DOI": "10.1234/semantic", "ArXiv": "2401.12345"},
            "openAccessPdf": {"url": "https://example.test/semantic.pdf"},
            "url": "https://www.semanticscholar.org/paper/S2-123",
        }
    )

    assert candidate.source == "semantic_scholar"
    assert candidate.external_id == "S2-123"
    assert candidate.title == "Semantic Scholar Local Agents"
    assert candidate.authors == "Jane Doe and John Smith"
    assert candidate.year == 2024
    assert candidate.doi == "10.1234/semantic"
    assert candidate.arxiv_id == "2401.12345"
    assert candidate.pdf_url == "https://example.test/semantic.pdf"
```

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_discovery.py -q
```

Expected: FAIL because the new normalization functions do not exist.

- [ ] **Step 2: Implement normalization helpers**

Add provider constants:

```python
CROSSREF_BASE_URL = "https://api.crossref.org"
SEMANTIC_SCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1"
SEMANTIC_SCHOLAR_FIELDS = (
    "paperId,title,authors,year,venue,abstract,externalIds,openAccessPdf,url"
)
```

Add:

```python
def normalize_crossref_work(work: dict[str, object]) -> DiscoveryCandidate:
    doi = _normalize_doi(_string_value(work.get("DOI")))
    return DiscoveryCandidate(
        source="crossref",
        external_id=doi or _clean_text(_string_value(work.get("URL"))) or "unknown",
        title=_clean_text(_first_string(work.get("title"))) or "Untitled",
        authors=_authors_from_crossref(work.get("author")),
        year=_year_from_crossref(work),
        doi=doi,
        venue=_clean_text(_first_string(work.get("container-title"))),
        abstract=_strip_markup(_clean_text(_string_value(work.get("abstract")))),
        arxiv_id=None,
        pdf_url=_crossref_pdf_url(work.get("link")),
        landing_url=_clean_text(_string_value(work.get("URL"))),
    )


def normalize_semantic_scholar_paper(paper: dict[str, object]) -> DiscoveryCandidate:
    external_ids = _dict_value(paper.get("externalIds"))
    return DiscoveryCandidate(
        source="semantic_scholar",
        external_id=_clean_text(_string_value(paper.get("paperId"))) or "unknown",
        title=_clean_text(_string_value(paper.get("title"))) or "Untitled",
        authors=_authors_from_semantic_scholar(paper.get("authors")),
        year=_int_value(paper.get("year")),
        doi=_normalize_doi(_string_value(external_ids.get("DOI"))),
        venue=_clean_text(_string_value(paper.get("venue"))),
        abstract=_clean_text(_string_value(paper.get("abstract"))),
        arxiv_id=_strip_arxiv_version(_string_value(external_ids.get("ArXiv")) or "")
        or None,
        pdf_url=_clean_text(_string_value(_dict_value(paper.get("openAccessPdf")).get("url"))),
        landing_url=_clean_text(_string_value(paper.get("url"))),
    )
```

Add small helpers for first list string, Crossref authors, Semantic Scholar authors, Crossref year extraction, Crossref PDF links, and simple markup stripping.

- [ ] **Step 3: Verify normalization tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_discovery.py -q
```

Expected: PASS.

## Task 2: Discovery Client Provider Fan-Out

**Files:**

- Modify: `backend/tests/test_discovery.py`
- Modify: `backend/src/knowledge_agent/discovery.py`

- [ ] **Step 1: Write failing client fan-out test**

Add this test:

```python
def test_external_discovery_client_queries_crossref_and_semantic_scholar():
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        host = request.url.host or ""
        if "openalex.org" in host:
            return httpx.Response(200, json={"results": []})
        if "arxiv.org" in host:
            return httpx.Response(
                200,
                text='<feed xmlns="http://www.w3.org/2005/Atom"></feed>',
            )
        if "crossref.org" in host:
            return httpx.Response(
                200,
                json={
                    "message": {
                        "items": [
                            {
                                "DOI": "10.1234/cross",
                                "title": ["Crossref Local Agents"],
                                "URL": "https://doi.org/10.1234/cross",
                            }
                        ]
                    }
                },
            )
        if "semanticscholar.org" in host:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "paperId": "S2-123",
                            "title": "Semantic Scholar Local Agents",
                            "externalIds": {"DOI": "10.1234/semantic"},
                        }
                    ]
                },
            )
        return httpx.Response(404)

    client = ExternalDiscoveryClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )

    candidates = client.search("local agents", limit=5)

    assert [candidate.source for candidate in candidates] == [
        "crossref",
        "semantic_scholar",
    ]
    assert any("api.crossref.org/works" in url for url in requested_urls)
    assert any("api.semanticscholar.org/graph/v1/paper/search" in url for url in requested_urls)
```

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_discovery.py::test_external_discovery_client_queries_crossref_and_semantic_scholar -q
```

Expected: FAIL because the client does not call Crossref or Semantic Scholar.

- [ ] **Step 2: Implement client provider calls**

In `ExternalDiscoveryClient.search`, add:

```python
candidates.extend(self._search_crossref(query_type, normalized_query, limit))
candidates.extend(self._search_semantic_scholar(query_type, normalized_query, limit))
```

Implement `_search_crossref`:

- For DOI, call `GET /works/{doi}` and normalize `payload["message"]`.
- For keyword/arXiv, call `GET /works` with `query.bibliographic` and `rows`.
- Catch all provider errors and return `[]`.

Implement `_search_semantic_scholar`:

- For DOI, call `GET /paper/DOI:{doi}` with `fields`.
- For arXiv, call `GET /paper/ARXIV:{arxiv_id}` with `fields`.
- For keyword/title, call `GET /paper/search` with `query`, `limit`, and `fields`.
- Normalize dict payloads from lookup calls and list payloads from search `data`.
- Catch all provider errors and return `[]`.

- [ ] **Step 3: Verify client tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_discovery.py -q
```

Expected: PASS.

## Task 3: Documentation and Final Verification

**Files:**

- Modify: `README.md`

- [ ] **Step 1: Update README discovery source text**

Change the current slice bullet:

```markdown
- External literature discovery with open PDF download/import.
```

to:

```markdown
- External literature discovery through OpenAlex, Crossref, Semantic Scholar, arXiv, and Unpaywall, with open PDF download/import.
```

- [ ] **Step 2: Run backend verification**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
```

Expected: all backend tests pass.

- [ ] **Step 3: Run repository hygiene check**

Run:

```powershell
git diff --check
```

Expected: no whitespace errors.

- [ ] **Step 4: Commit**

```powershell
git add docs/superpowers/plans/2026-06-05-crossref-semantic-scholar-discovery-plan.md backend/src/knowledge_agent/discovery.py backend/tests/test_discovery.py README.md
git commit -m "feat: add crossref semantic scholar discovery"
```

## Self-Review Notes

- Spec coverage: Covers the approved design goal to retrieve metadata from Crossref and Semantic Scholar alongside existing arXiv, OpenAlex, and Unpaywall discovery.
- Placeholder scan: No TBD/TODO placeholders remain.
- Type consistency: New providers continue to use the existing `DiscoveryCandidate` model and existing API response schema.
