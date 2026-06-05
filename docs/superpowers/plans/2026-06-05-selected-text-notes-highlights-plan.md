# Selected Text Notes and Highlights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user select text while reading, ask for Chinese translation or explanation with page/source traceability, and save useful selected passages or assistant answers as local notes/highlights.

**Architecture:** Keep this slice on the existing extracted-text reader rather than replacing the reader with PDF.js. Add SQLite-backed `notes` and `highlights`, add a selected-text assistant path that sends only the selected span to the configured provider, then expose compact desktop controls for selecting text, translating/explaining it, highlighting it, and saving answers as notes.

**Tech Stack:** Python 3.13, FastAPI, SQLite, pytest, React, TypeScript, Vitest, Testing Library.

---

## Scope

This plan implements:

- `notes` and `highlights` SQLite tables.
- Repository methods to create/list notes and highlights per paper.
- Selected-text assistant service and API endpoint.
- Note/highlight API endpoints.
- Desktop text selection capture from the current reader page.
- Assistant panel controls for `Translate selection`, `Explain selection`, `Highlight selection`, and `Save answer as note`.
- Notes/highlights display for the currently open paper.

This plan does not implement binary PDF canvas rendering, exact PDF coordinate annotations, color pickers beyond a fixed default color, rich note editing, tags/favorites, or cross-paper/library-wide synthesis.

## File Structure

Create or modify:

```text
backend/
  src/knowledge_agent/
    assistant.py
    db.py
    main.py
    models.py
    repositories.py
    schemas.py
  tests/
    test_api.py
    test_assistant.py
    test_database.py
apps/
  desktop/
    src/
      App.test.tsx
      App.tsx
      api.ts
      styles.css
docs/
  superpowers/plans/2026-06-05-selected-text-notes-highlights-plan.md
```

Responsibilities:

- `backend/src/knowledge_agent/db.py`: Create `notes` and `highlights` tables with migration guards.
- `backend/src/knowledge_agent/models.py`: Add `Note` and `Highlight` dataclasses; allow selection citations with no chunk ID.
- `backend/src/knowledge_agent/repositories.py`: Add `NotesRepository` and `HighlightsRepository`.
- `backend/src/knowledge_agent/assistant.py`: Add selected-text translation/explanation prompt assembly.
- `backend/src/knowledge_agent/main.py`: Add selected assistant, note, and highlight endpoints.
- `backend/src/knowledge_agent/schemas.py`: Add note/highlight and selected assistant request/response schemas.
- `apps/desktop/src/api.ts`: Add typed client methods for selected assistant, notes, and highlights.
- `apps/desktop/src/App.tsx`: Capture reader text selection and wire assistant/note/highlight controls.

## Task 1: Notes and Highlights Persistence

**Files:**
- Modify: `backend/src/knowledge_agent/db.py`
- Modify: `backend/src/knowledge_agent/models.py`
- Modify: `backend/src/knowledge_agent/repositories.py`
- Modify: `backend/tests/test_database.py`

- [ ] **Step 1: Write failing persistence tests**

Add tests to `backend/tests/test_database.py` proving:

- `init_db` creates `notes` and `highlights`.
- `NotesRepository.create` stores body, linked paper, page, source span, selected text, note type, and optional Q&A ID.
- `NotesRepository.list_for_paper` returns newest notes first.
- `HighlightsRepository.create` stores selected text, page, source span, color, and optional note ID.
- `HighlightsRepository.list_for_paper` returns highlights for one paper only.

Use this shape:

```python
from knowledge_agent.repositories import HighlightsRepository, NotesRepository


def test_notes_and_highlights_roundtrip(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        papers = PapersRepository(conn)
        notes = NotesRepository(conn)
        highlights = HighlightsRepository(conn)
        paper = papers.create(title="Readable Paper", year=2026, doi=None)
        other_paper = papers.create(title="Other Paper", year=2026, doi=None)

        note = notes.create(
            paper_id=paper.id,
            body="This answer is worth keeping.",
            page_number=2,
            source_span="page:2:selection",
            selected_text="retrieval augmented generation",
            note_type="assistant_answer",
            qna_id=None,
        )
        highlight = highlights.create(
            paper_id=paper.id,
            page_number=2,
            source_span="page:2:selection",
            selected_text="retrieval augmented generation",
            color="yellow",
            note_id=note.id,
        )
        highlights.create(
            paper_id=other_paper.id,
            page_number=1,
            source_span="page:1:selection",
            selected_text="other",
            color="yellow",
            note_id=None,
        )
        paper_notes = notes.list_for_paper(paper.id)
        paper_highlights = highlights.list_for_paper(paper.id)

    assert note.body == "This answer is worth keeping."
    assert paper_notes[0].selected_text == "retrieval augmented generation"
    assert paper_notes[0].note_type == "assistant_answer"
    assert highlight.note_id == note.id
    assert len(paper_highlights) == 1
    assert paper_highlights[0].page_number == 2
```

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py -q
```

Expected: FAIL because `NotesRepository` and `HighlightsRepository` do not exist.

- [ ] **Step 2: Implement persistence**

Add dataclasses:

```python
@dataclass(frozen=True)
class Note:
    id: int
    paper_id: int
    body: str
    page_number: int | None
    source_span: str | None
    selected_text: str | None
    note_type: str
    qna_id: int | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Highlight:
    id: int
    paper_id: int
    page_number: int
    source_span: str
    selected_text: str
    color: str
    note_id: int | None
    created_at: str
```

Add tables:

```sql
create table if not exists notes (
    id integer primary key autoincrement,
    paper_id integer not null references papers(id) on delete cascade,
    body text not null,
    page_number integer,
    source_span text,
    selected_text text,
    note_type text not null default 'manual',
    qna_id integer references qna_entries(id) on delete set null,
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp
);

create table if not exists highlights (
    id integer primary key autoincrement,
    paper_id integer not null references papers(id) on delete cascade,
    page_number integer not null,
    source_span text not null,
    selected_text text not null,
    color text not null default 'yellow',
    note_id integer references notes(id) on delete set null,
    created_at text not null default current_timestamp
);
```

Add `NotesRepository` with `create` and `list_for_paper`. Add `HighlightsRepository` with `create` and `list_for_paper`.

- [ ] **Step 3: Verify persistence tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add backend/src/knowledge_agent/db.py backend/src/knowledge_agent/models.py backend/src/knowledge_agent/repositories.py backend/tests/test_database.py
git commit -m "feat: store notes and highlights"
```

## Task 2: Selected-Text Assistant and APIs

**Files:**
- Modify: `backend/src/knowledge_agent/assistant.py`
- Modify: `backend/src/knowledge_agent/main.py`
- Modify: `backend/src/knowledge_agent/models.py`
- Modify: `backend/src/knowledge_agent/schemas.py`
- Modify: `backend/tests/test_assistant.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing selected assistant tests**

Add tests to `backend/tests/test_assistant.py` proving:

- Selected-text translation sends only the selected text and source span to the provider.
- Selected-text explanation returns a citation with paper title, page number, selected snippet, and source span.
- Blank selected text raises `ValueError("selected text is required")`.
- Provider setting enforcement matches current-paper Q&A.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_assistant.py -q
```

Expected: FAIL because `answer_selected_text` does not exist.

- [ ] **Step 2: Implement selected assistant service**

Add:

```python
def answer_selected_text(
    conn,
    paper_id: int,
    selected_text: str,
    page_number: int,
    source_span: str,
    action: str,
    chat_provider: ChatProvider,
    instruction: str | None = None,
) -> TraceableAnswer:
    ...
```

Supported actions are `translate`, `explain`, and `summarize`. Build a Chinese prompt that includes:

- Current paper title.
- Page number.
- Source span.
- Selected text.
- User instruction when provided.

Set citation `chunk_id=None`, `mode="selection"`, and save the result through `QnaRepository` with a question like `translate selected text` or `explain selected text`.

- [ ] **Step 3: Write failing API tests**

Add tests to `backend/tests/test_api.py` proving:

- `POST /api/papers/{paper_id}/assistant/selection` returns the answer and selection citation.
- `POST /api/notes` creates a note; `GET /api/papers/{paper_id}/notes` lists it.
- `POST /api/highlights` creates a highlight; `GET /api/papers/{paper_id}/highlights` lists it.
- Missing paper returns 404.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py -q
```

Expected: FAIL because selected assistant, notes, and highlights endpoints are missing.

- [ ] **Step 4: Implement schemas and endpoints**

Add schemas:

```python
class SelectedTextAssistantRequest(BaseModel):
    selected_text: str = Field(min_length=1)
    page_number: int
    source_span: str = Field(min_length=1)
    action: str = Field(pattern="^(translate|explain|summarize)$")
    instruction: str | None = None

class CreateNoteRequest(BaseModel):
    paper_id: int
    body: str = Field(min_length=1)
    page_number: int | None = None
    source_span: str | None = None
    selected_text: str | None = None
    note_type: str = Field(default="manual", pattern="^(manual|assistant_answer|selection)$")
    qna_id: int | None = None

class CreateHighlightRequest(BaseModel):
    paper_id: int
    page_number: int
    source_span: str = Field(min_length=1)
    selected_text: str = Field(min_length=1)
    color: str = "yellow"
    note_id: int | None = None
```

Add response models with `from_attributes=True`. Add endpoints:

- `POST /api/papers/{paper_id}/assistant/selection`
- `POST /api/notes`
- `GET /api/papers/{paper_id}/notes`
- `POST /api/highlights`
- `GET /api/papers/{paper_id}/highlights`

- [ ] **Step 5: Verify backend API tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_assistant.py backend/tests/test_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/src/knowledge_agent/assistant.py backend/src/knowledge_agent/main.py backend/src/knowledge_agent/models.py backend/src/knowledge_agent/schemas.py backend/tests/test_assistant.py backend/tests/test_api.py
git commit -m "feat: add selected text assistant and note APIs"
```

## Task 3: Desktop Selection, Notes, and Highlights Workflow

**Files:**
- Modify: `apps/desktop/src/api.ts`
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Write failing frontend tests**

Add tests proving:

- Selecting text in the reader shows the selected text in the assistant panel.
- `Translate selection` posts to `/api/papers/{paper_id}/assistant/selection` and displays the answer citation.
- `Explain selection` uses action `explain`.
- `Highlight selection` creates a highlight and shows it in the paper notes area.
- `Save answer as note` creates a note and shows it in the paper notes area.

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
```

Expected: FAIL because selection, selected assistant, notes, and highlights UI are missing.

- [ ] **Step 2: Implement API client calls**

Add types and methods:

```ts
export type Note = { ... };
export type Highlight = { ... };

export async function askSelectedText(...): Promise<AskPaperQuestionResponse>;
export async function createNote(...): Promise<Note>;
export async function listNotes(paperId: number): Promise<{ notes: Note[] }>;
export async function createHighlight(...): Promise<Highlight>;
export async function listHighlights(paperId: number): Promise<{ highlights: Highlight[] }>;
```

- [ ] **Step 3: Implement desktop UI**

Update the reader:

- Each rendered page receives an `onMouseUp` handler.
- The handler reads `window.getSelection()?.toString().trim()`.
- Store `selectedText`, `selectedPageNumber`, and `selectedSourceSpan` as `page:<page>:selection`.

Update the assistant panel:

- Show selected text when present.
- Add `Translate selection`, `Explain selection`, `Highlight selection`, and `Save answer as note`.
- Disable selection actions when no paper is open or no selected text exists.
- Load notes/highlights whenever a paper opens.
- Show notes and highlights in a compact paper notes section.

- [ ] **Step 4: Verify frontend tests pass**

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add apps/desktop/src/api.ts apps/desktop/src/App.test.tsx apps/desktop/src/App.tsx apps/desktop/src/styles.css
git commit -m "feat: add desktop selected text notes workflow"
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

- Spec coverage: Covers selected-text translation/explanation, saving useful answers as notes, selected passage notes, and text highlights. Exact PDF coordinate highlights remain for the later PDF.js reader slice.
- Placeholder scan: No unfinished placeholder markers or unspecified test commands remain.
- Type consistency: `Note`, `Highlight`, selected assistant request fields, and frontend types use the same `paper_id`, `page_number`, `source_span`, and `selected_text` names.
