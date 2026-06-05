# Minimal Vector Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent local chunk vector index and semantic fallback for local search without requiring a cloud embedding provider.

**Architecture:** Keep SQLite as the canonical metadata store and add a rebuildable `chunk_vectors` mapping table. Store deterministic local chunk vectors under `indexes/vectors/chunks.json`; `ChunksRepository` stays responsible for chunk rows and FTS, while `vector_index.py` owns embedding, persistence, similarity ranking, and rebuild behavior. `/api/search/local` keeps the existing response schema and blends FTS hits, semantic hits, then metadata hits.

**Tech Stack:** Python 3.13, FastAPI, SQLite, pytest, standard-library JSON/hash/math.

---

## Scope

This plan implements:

- A persistent local vector index directory under each managed library at `indexes/vectors/`.
- A `chunk_vectors` SQLite table that maps chunk IDs to vector IDs and the local embedding model name.
- Deterministic local text embeddings so the MVP works offline before Ollama/cloud embeddings are configured.
- Rebuild-on-import behavior when document chunks are replaced.
- Semantic local search fallback when exact FTS does not find page-level hits.
- README documentation for the local vector index behavior and future provider upgrade path.

This plan does not implement Chroma integration, remote embedding calls, frontend UI changes, assistant streaming, cross-paper synthesis UI, or background vector rebuild jobs.

## File Structure

Create:

```text
backend/src/knowledge_agent/vector_index.py
backend/tests/test_vector_index.py
```

Modify:

```text
backend/src/knowledge_agent/config.py
backend/src/knowledge_agent/db.py
backend/src/knowledge_agent/import_service.py
backend/src/knowledge_agent/main.py
backend/src/knowledge_agent/repositories.py
backend/tests/test_api.py
backend/tests/test_database.py
backend/tests/test_import_service.py
README.md
docs/superpowers/plans/2026-06-05-minimal-vector-search-plan.md
```

Responsibilities:

- `vector_index.py`: Deterministic embedding, JSON persistence, vector entry upsert/delete, cosine-style ranking, and converting semantic results to chunk IDs.
- `db.py`: Create `chunk_vectors` and migrate existing databases.
- `config.py`: Expose `vector_index_path` under the active managed library.
- `repositories.py`: Record vector ID mappings and support loading chunks by ID.
- `import_service.py`: Rebuild vector entries after PDF parsing replaces document chunks.
- `main.py`: Pass the active vector index path into local search.
- Tests: Prove persistence, mapping cleanup, import-time indexing, and semantic local search fallback.

## Task 1: Vector Index Persistence

**Files:**

- Create: `backend/tests/test_vector_index.py`
- Create: `backend/src/knowledge_agent/vector_index.py`

- [ ] **Step 1: Write failing vector index tests**

Create `backend/tests/test_vector_index.py` with tests proving:

```python
from knowledge_agent.vector_index import LocalVectorIndex, embed_text


def test_embed_text_places_related_terms_near_each_other():
    query = embed_text("neural retrieval")
    related = embed_text("retrieval augmented generation")
    unrelated = embed_text("green tea protocol")

    assert query.similarity(related) > query.similarity(unrelated)


def test_local_vector_index_persists_entries(tmp_path):
    index_path = tmp_path / "library" / "indexes" / "vectors" / "chunks.json"
    index = LocalVectorIndex(index_path)
    index.replace_document_entries(
        document_id=10,
        entries=[
            (1, "neural retrieval systems"),
            (2, "green tea protocol"),
        ],
    )

    reloaded = LocalVectorIndex(index_path)

    assert reloaded.search("retrieval", limit=1)[0].chunk_id == 1
    assert index_path.exists()
```

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_vector_index.py -q
```

Expected: FAIL because `knowledge_agent.vector_index` does not exist.

- [ ] **Step 2: Implement minimal local vector index**

Create `backend/src/knowledge_agent/vector_index.py` with:

- `LOCAL_EMBEDDING_MODEL = "local-hashing-v1"`.
- `EmbeddedText` dataclass containing a normalized tuple of floats and `similarity()`.
- `VectorSearchResult` dataclass with `chunk_id` and `score`.
- `embed_text(text: str, dimensions: int = 128) -> EmbeddedText`, using token hashing into a fixed-size vector and L2 normalization.
- `LocalVectorIndex(index_path: Path)` with `replace_document_entries(document_id, entries)`, `delete_document(document_id)`, and `search(query, limit)`.

Persist JSON as:

```json
{
  "model": "local-hashing-v1",
  "dimensions": 128,
  "entries": [
    {"document_id": 10, "chunk_id": 1, "text": "neural retrieval systems", "vector": [0.0]}
  ]
}
```

- [ ] **Step 3: Verify vector index tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_vector_index.py -q
```

Expected: PASS.

## Task 2: SQLite Mapping and Import-Time Indexing

**Files:**

- Modify: `backend/src/knowledge_agent/config.py`
- Modify: `backend/src/knowledge_agent/db.py`
- Modify: `backend/src/knowledge_agent/import_service.py`
- Modify: `backend/src/knowledge_agent/repositories.py`
- Modify: `backend/tests/test_database.py`
- Modify: `backend/tests/test_import_service.py`

- [ ] **Step 1: Write failing persistence tests**

Add tests proving:

- `init_db` creates `chunk_vectors`.
- `ChunksRepository.replace_vector_mappings()` replaces stale mappings for a document.
- `import_pdf()` writes `indexes/vectors/chunks.json` and creates one vector mapping per extracted chunk.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py::test_init_db_creates_tables backend/tests/test_database.py::test_chunks_replace_vector_mappings_for_document backend/tests/test_import_service.py::test_import_pdf_builds_vector_index_for_chunks -q
```

Expected: FAIL because the table, repository methods, and import-time indexing are missing.

- [ ] **Step 2: Implement mapping and import integration**

Add `AppConfig.vector_index_path`:

```python
@property
def vector_index_path(self) -> Path:
    return self.library_dir / "indexes" / "vectors" / "chunks.json"
```

Add table:

```sql
create table if not exists chunk_vectors (
    chunk_id integer primary key references chunks(id) on delete cascade,
    paper_id integer not null references papers(id) on delete cascade,
    document_id integer not null references documents(id) on delete cascade,
    vector_id text not null unique,
    embedding_model text not null,
    updated_at text not null default current_timestamp
);

create index if not exists idx_chunk_vectors_document_id
on chunk_vectors(document_id);
```

Add repository methods:

```python
def replace_vector_mappings(self, document_id: int, mappings: list[tuple[int, str, str]]) -> None:
    ...

def vector_mapping_count_for_document(self, document_id: int) -> int:
    ...

def get_many(self, chunk_ids: list[int]) -> list[Chunk]:
    ...
```

Change `import_pdf()` to accept optional `vector_index_path: Path | None = None`. After `_parse_imported_document` stores chunks successfully, rebuild vector entries for the document and write `chunk_vectors` mappings.

- [ ] **Step 3: Verify mapping/import tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py backend/tests/test_import_service.py -q
```

Expected: PASS.

## Task 3: Semantic Local Search Fallback

**Files:**

- Modify: `backend/src/knowledge_agent/main.py`
- Modify: `backend/src/knowledge_agent/repositories.py`
- Modify: `backend/tests/test_api.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing semantic search API test**

Add a test proving `/api/search/local?q=retrieval generation` can find a chunk that does not exact-match FTS but is semantically close through the vector index:

```python
def test_local_search_uses_semantic_vector_fallback(tmp_path: Path, write_pdf):
    source = write_pdf(
        tmp_path / "Semantic Paper.pdf",
        [
            "The method studies retrieval augmented generation for local papers.",
            "The appendix discusses ceramic kiln temperatures.",
        ],
    )
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))
    client.post("/api/imports/pdf", json={"source_path": str(source)})

    response = client.get("/api/search/local", params={"q": "retrieval generation"})

    assert response.status_code == 200
    hit = response.json()["hits"][0]
    assert hit["title"] == "Semantic Paper"
    assert hit["page_number"] == 1
    assert "retrieval augmented generation" in hit["snippet"]
```

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py::test_local_search_uses_semantic_vector_fallback -q
```

Expected: FAIL because local search does not load the vector index.

- [ ] **Step 2: Implement semantic fallback**

Update `ChunksRepository.search()` to accept:

```python
def search(
    self,
    query: str,
    limit: int = 25,
    semantic_chunk_ids: list[int] | None = None,
) -> list[SearchHit]:
    ...
```

After FTS hits and before metadata hits, add `_chunk_hits_by_ids()` for semantic chunk IDs not already returned. Preserve FTS ordering first.

Update `/api/search/local` in `main.py` to:

1. Load `LocalVectorIndex(config.vector_index_path)`.
2. Search semantic chunk IDs for the query.
3. Pass those IDs to `ChunksRepository.search(query, semantic_chunk_ids=...)`.
4. If the vector index is missing or unreadable, keep existing FTS/metadata behavior.

- [ ] **Step 3: Update README**

Add a short sentence to Current Slice:

```markdown
- Persistent local vector index under `indexes/vectors/` for semantic local search fallback.
```

- [ ] **Step 4: Verify semantic search and backend tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
git diff --check
```

Expected: all tests pass and no whitespace errors.

- [ ] **Step 5: Commit**

```powershell
git add backend/src/knowledge_agent/config.py backend/src/knowledge_agent/db.py backend/src/knowledge_agent/import_service.py backend/src/knowledge_agent/main.py backend/src/knowledge_agent/repositories.py backend/src/knowledge_agent/vector_index.py backend/tests/test_api.py backend/tests/test_database.py backend/tests/test_import_service.py backend/tests/test_vector_index.py README.md docs/superpowers/plans/2026-06-05-minimal-vector-search-plan.md
git commit -m "feat: add local vector search fallback"
```

## Self-Review Notes

- Spec coverage: Adds a persistent local vector index path and semantic local search behavior while keeping all source traceability in SQLite chunk rows.
- Placeholder scan: No TBD/TODO placeholders remain.
- Type consistency: The public API response shape remains unchanged; vector mappings are internal and rebuildable.
