# Desktop UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the desktop UI into a reader-centered research workspace while preserving existing backend APIs and MVP behavior.

**Architecture:** Keep `apps/desktop/src/api.ts` unchanged. Refactor `apps/desktop/src/App.tsx` from a single always-visible control panel into a stateful shell that renders a top app bar, library rail, reader workspace, assistant rail, dialogs, and drawers. Rewrite `apps/desktop/src/styles.css` around the new shell and update `apps/desktop/src/App.test.tsx` with TDD tests for the new workflow entry points.

**Tech Stack:** React 18, TypeScript, Vitest, Testing Library, CSS, Tauri desktop shell.

---

## File Structure

Create focused frontend components under `apps/desktop/src/components/`:

- `TopBar.tsx`: product identity, backend/library status, global search, and buttons for import/discover/jobs/settings.
- `LibraryRail.tsx`: paper list, segmented filters, tag filter, active paper state, favorite/tag controls.
- `ReaderWorkspace.tsx`: no-paper onboarding, paper header, PDF/text tabs, reader page navigation, selected-text toolbar.
- `AssistantRail.tsx`: current paper context, provider callout, ask composer, latest answer, citations, notes/highlights tabs.
- `ImportDialog.tsx`: PDF/folder/bibliography import and bibliography export.
- `DiscoverDrawer.tsx`: external search results and open PDF import flow.
- `JobsDrawer.tsx`: recent jobs, progress, failures, retry.
- `SettingsDialog.tsx`: library location and model provider settings.

Modify existing files:

- `apps/desktop/src/App.tsx`: orchestrates state, data loading, API handlers, dialog/drawer state, and passes props into components.
- `apps/desktop/src/App.test.tsx`: replaces always-visible form expectations with workflow tests.
- `apps/desktop/src/styles.css`: rewrites layout and visual style.

Do not modify backend files in this plan. The current `/api/papers` payload does not include document parse status, so paper cards use available metadata, favorite, and tag state. Parse status remains visible in the reader header after `reader-context` is loaded.

---

### Task 1: Reader-Centered Shell

**Files:**
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Create: `apps/desktop/src/components/TopBar.tsx`
- Create: `apps/desktop/src/components/LibraryRail.tsx`
- Create: `apps/desktop/src/components/ReaderWorkspace.tsx`
- Create: `apps/desktop/src/components/AssistantRail.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Write failing shell test**

Add this test near the first load tests in `apps/desktop/src/App.test.tsx`:

```tsx
it("shows a reader-centered shell and hides low-frequency controls by default", async () => {
  fetchMock
    .mockResolvedValueOnce(jsonResponse({ status: "ok", service: "knowledge-agent-backend" }))
    .mockResolvedValueOnce(jsonResponse(defaultLibraryStatus))
    .mockResolvedValueOnce(jsonResponse({ papers: [] }))
    .mockResolvedValueOnce(jsonResponse(defaultProviderSettings))
    .mockResolvedValueOnce(jsonResponse(emptyJobsResponse));

  render(<App />);

  expect(await screen.findByRole("banner", { name: "Thesis Assistant workspace" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Thesis Assistant" })).toBeInTheDocument();
  expect(screen.getByText("Backend ok")).toBeInTheDocument();
  expect(screen.getByText("0 papers")).toBeInTheDocument();
  expect(screen.getByRole("searchbox", { name: "Search library or DOI" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Import" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Discover" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Jobs" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Settings" })).toBeInTheDocument();

  expect(screen.getByRole("navigation", { name: "Library" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Start your research library" })).toBeInTheDocument();
  expect(screen.getByText("Import papers or discover literature to begin reading with cited context.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Import papers" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Discover literature" })).toBeInTheDocument();
  expect(screen.getByText("Configure a model provider to ask questions about the current paper.")).toBeInTheDocument();

  expect(screen.queryByLabelText("PDF source path")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("PDF folder path")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Bibliography source path")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Provider")).not.toBeInTheDocument();
  expect(screen.queryByText("No recent jobs.")).not.toBeInTheDocument();
  expect(screen.queryByText("No search hits.")).not.toBeInTheDocument();
  expect(screen.queryByText("No external results.")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run shell test to verify RED**

Run from `apps/desktop`:

```powershell
npm test -- src/App.test.tsx -t "shows a reader-centered shell"
```

Expected: FAIL because the current UI has no `Thesis Assistant workspace` banner and still shows the old always-visible forms.

- [ ] **Step 3: Create shell components**

Create `apps/desktop/src/components/TopBar.tsx`:

```tsx
type TopBarProps = {
  backendStatus: string;
  paperCount: number;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  onSearchSubmit: () => void;
  onOpenImport: () => void;
  onOpenDiscover: () => void;
  onOpenJobs: () => void;
  onOpenSettings: () => void;
  activeJobCount: number;
};

export function TopBar({
  backendStatus,
  paperCount,
  searchQuery,
  onSearchQueryChange,
  onSearchSubmit,
  onOpenImport,
  onOpenDiscover,
  onOpenJobs,
  onOpenSettings,
  activeJobCount,
}: TopBarProps) {
  return (
    <header aria-label="Thesis Assistant workspace" className="top-bar">
      <div className="brand-block">
        <h1>Thesis Assistant</h1>
        <div className="status-row" aria-label="Workspace status">
          <span className="status-pill ready">Backend {backendStatus}</span>
          <span className="status-pill">{paperCount} papers</span>
        </div>
      </div>
      <form
        aria-label="Global library search"
        className="global-search"
        onSubmit={(event) => {
          event.preventDefault();
          onSearchSubmit();
        }}
      >
        <input
          aria-label="Search library or DOI"
          placeholder="Search library or paste DOI/title/arXiv"
          type="search"
          value={searchQuery}
          onChange={(event) => onSearchQueryChange(event.target.value)}
        />
      </form>
      <div className="top-actions">
        <button type="button" onClick={onOpenImport}>Import</button>
        <button type="button" onClick={onOpenDiscover}>Discover</button>
        <button type="button" onClick={onOpenJobs}>
          Jobs{activeJobCount > 0 ? ` ${activeJobCount}` : ""}
        </button>
        <button type="button" onClick={onOpenSettings}>Settings</button>
      </div>
    </header>
  );
}
```

Create `apps/desktop/src/components/LibraryRail.tsx`:

```tsx
import { FormEvent } from "react";
import type { Paper, SearchHit } from "../api";

type LibraryRailProps = {
  papers: Paper[];
  activePaperId: number | null;
  favoriteFilter: boolean;
  tagFilter: string;
  tagInputs: Record<number, string>;
  searchHits: SearchHit[];
  searchPerformed: boolean;
  onOpenPaper: (paper: Paper) => void;
  onToggleFavorite: (paper: Paper) => void;
  onFavoriteFilterChange: (value: boolean) => void;
  onTagFilterChange: (value: string) => void;
  onApplyFilters: () => void;
  onTagInputChange: (paperId: number, value: string) => void;
  onAddTag: (event: FormEvent<HTMLFormElement>, paper: Paper) => void;
  onRemoveTag: (paper: Paper, tagName: string) => void;
  paperMetadata: (paper: Paper) => string;
  paperFromSearchHit: (hit: SearchHit) => Paper;
};

export function LibraryRail({
  papers,
  activePaperId,
  favoriteFilter,
  tagFilter,
  tagInputs,
  searchHits,
  searchPerformed,
  onOpenPaper,
  onToggleFavorite,
  onFavoriteFilterChange,
  onTagFilterChange,
  onApplyFilters,
  onTagInputChange,
  onAddTag,
  onRemoveTag,
  paperMetadata,
  paperFromSearchHit,
}: LibraryRailProps) {
  return (
    <nav aria-label="Library" className="library-rail">
      <div className="rail-header">
        <div>
          <h2>Library</h2>
          <p>{papers.length} papers in this view</p>
        </div>
      </div>
      <div aria-label="Library filters" className="segmented-control">
        <button className={!favoriteFilter ? "active" : ""} onClick={() => onFavoriteFilterChange(false)} type="button">
          All
        </button>
        <button className={favoriteFilter ? "active" : ""} onClick={() => onFavoriteFilterChange(true)} type="button">
          Favorites
        </button>
      </div>
      <form
        className="tag-filter-form"
        onSubmit={(event) => {
          event.preventDefault();
          onApplyFilters();
        }}
      >
        <label htmlFor="tag-filter">Tag filter</label>
        <div className="compact-row">
          <input
            id="tag-filter"
            value={tagFilter}
            onChange={(event) => onTagFilterChange(event.target.value)}
            placeholder="reading"
          />
          <button type="submit">Apply</button>
        </div>
      </form>
      <div className="paper-list">
        {papers.length === 0 ? (
          <p className="empty compact">No papers in this library yet.</p>
        ) : (
          papers.map((paper) => (
            <article className={activePaperId === paper.id ? "paper-card active" : "paper-card"} key={paper.id}>
              <button className="paper-open" onClick={() => onOpenPaper(paper)} type="button" aria-label={`Open ${paper.title}`}>
                <span className="paper-title">{paper.title}</span>
                <span className="paper-meta">{paperMetadata(paper)}</span>
              </button>
              <div className="paper-card-actions">
                <button
                  className={paper.favorite ? "chip active" : "chip"}
                  onClick={() => onToggleFavorite(paper)}
                  type="button"
                  aria-label={paper.favorite ? `Remove ${paper.title} from favorites` : `Mark ${paper.title} as favorite`}
                >
                  {paper.favorite ? "Favorited" : "Favorite"}
                </button>
              </div>
              {paper.tags.length > 0 ? (
                <div className="tag-list" aria-label={`Tags for ${paper.title}`}>
                  {paper.tags.map((tag) => (
                    <button className="tag-pill" key={tag} onClick={() => onRemoveTag(paper, tag)} type="button" aria-label={`Remove tag ${tag} from ${paper.title}`}>
                      {tag}
                    </button>
                  ))}
                </div>
              ) : null}
              <form className="tag-form" onSubmit={(event) => onAddTag(event, paper)}>
                <input
                  aria-label={`Tag ${paper.title}`}
                  value={tagInputs[paper.id] ?? ""}
                  onChange={(event) => onTagInputChange(paper.id, event.target.value)}
                  placeholder="Add tag"
                />
                <button type="submit" aria-label={`Add tag to ${paper.title}`} disabled={(tagInputs[paper.id] ?? "").trim().length === 0}>
                  Add
                </button>
              </form>
            </article>
          ))
        )}
      </div>
      {searchPerformed ? (
        <section className="rail-section" aria-labelledby="local-search-heading">
          <h3 id="local-search-heading">Search results</h3>
          {searchHits.length === 0 ? (
            <p className="empty compact">No local matches.</p>
          ) : (
            <div className="search-list">
              {searchHits.map((hit) =>
                hit.page_number === null || hit.chunk_id === null ? (
                  <article className="search-result-card" key={`metadata-${hit.paper_id}`}>
                    <span className="paper-title">{hit.title}</span>
                    <span className="page-label">Metadata match</span>
                    <span className="snippet">{hit.snippet}</span>
                  </article>
                ) : (
                  <button className="search-result-card" key={hit.chunk_id} onClick={() => onOpenPaper(paperFromSearchHit(hit))} type="button" aria-label={`Open ${hit.title} page ${hit.page_number}`}>
                    <span className="paper-title">{hit.title}</span>
                    <span className="page-label">Page {hit.page_number}</span>
                    <span className="snippet">{hit.snippet}</span>
                  </button>
                ),
              )}
            </div>
          )}
        </section>
      ) : null}
    </nav>
  );
}
```

Create `apps/desktop/src/components/ReaderWorkspace.tsx`:

```tsx
import type { ReaderContext } from "../api";

type ReaderWorkspaceProps = {
  readerContext: ReaderContext | null;
  activeReaderPage: number | null;
  selectedText: string;
  selectedPageNumber: number | null;
  selectionBusy: boolean;
  pdfPreviewUrl: string;
  onOpenImport: () => void;
  onOpenDiscover: () => void;
  onReaderPageMouseUp: (pageNumber: number) => void;
  onSelectionAction: (action: "translate" | "explain" | "summarize") => void;
  onHighlightSelection: () => void;
  onSaveSelectionAsNote: () => void;
};

export function ReaderWorkspace({
  readerContext,
  activeReaderPage,
  selectedText,
  selectedPageNumber,
  selectionBusy,
  pdfPreviewUrl,
  onOpenImport,
  onOpenDiscover,
  onReaderPageMouseUp,
  onSelectionAction,
  onHighlightSelection,
  onSaveSelectionAsNote,
}: ReaderWorkspaceProps) {
  const selectionReady = selectedText.trim().length > 0 && selectedPageNumber !== null;
  if (!readerContext) {
    return (
      <section className="reader-workspace empty-reader" aria-label="Reader workspace">
        <div className="onboarding-panel">
          <p className="eyebrow">Local research workspace</p>
          <h2>Start your research library</h2>
          <p>Import papers or discover literature to begin reading with cited context.</p>
          <div className="onboarding-actions">
            <button type="button" onClick={onOpenImport}>Import papers</button>
            <button type="button" onClick={onOpenDiscover}>Discover literature</button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="reader-workspace" aria-label="Reader workspace">
      <header className="reader-header">
        <div>
          <h2>{readerContext.paper.title}</h2>
          <p>{readerContext.document.parse_status} · {readerContext.document.page_count ?? readerContext.pages.length} pages</p>
        </div>
      </header>
      {selectionReady ? (
        <div className="selection-toolbar" role="toolbar" aria-label="Selected text actions">
          <span>Page {selectedPageNumber}</span>
          <button type="button" disabled={selectionBusy} onClick={() => onSelectionAction("translate")}>Translate</button>
          <button type="button" disabled={selectionBusy} onClick={() => onSelectionAction("explain")}>Explain</button>
          <button type="button" disabled={selectionBusy} onClick={onHighlightSelection}>Highlight</button>
          <button type="button" disabled={selectionBusy} onClick={onSaveSelectionAsNote}>Note</button>
        </div>
      ) : null}
      <div className="reader-grid">
        <iframe className="pdf-preview" src={pdfPreviewUrl} title={`PDF reader for ${readerContext.paper.title}`} />
        <section className="extracted-text-layer" aria-label="Extracted text">
          {readerContext.pages.map((page) => (
            <article
              aria-current={activeReaderPage === page.page_number ? "page" : undefined}
              aria-label={`Reader page ${page.page_number}`}
              className={activeReaderPage === page.page_number ? "reader-page active" : "reader-page"}
              id={`reader-page-${page.page_number}`}
              key={page.page_number}
              onMouseUp={() => onReaderPageMouseUp(page.page_number)}
            >
              <h3>Page {page.page_number}</h3>
              <p>{page.text}</p>
            </article>
          ))}
        </section>
      </div>
    </section>
  );
}
```

Create `apps/desktop/src/components/AssistantRail.tsx`:

```tsx
import { FormEvent } from "react";
import type { AskPaperQuestionResponse, Highlight, Note, ProviderSettings, ReaderContext } from "../api";

type AssistantRailProps = {
  readerContext: ReaderContext | null;
  providerSettings: ProviderSettings | null;
  question: string;
  assistantProgress: string;
  assistantAnswer: AskPaperQuestionResponse | null;
  notes: Note[];
  highlights: Highlight[];
  notesView: "notes" | "highlights";
  onQuestionChange: (value: string) => void;
  onAsk: (event: FormEvent<HTMLFormElement>) => void;
  onOpenSettings: () => void;
  onOpenReaderPage: (pageNumber: number) => void;
  onSaveAnswerAsNote: () => void;
  onNotesViewChange: (view: "notes" | "highlights") => void;
};

export function AssistantRail({
  readerContext,
  providerSettings,
  question,
  assistantProgress,
  assistantAnswer,
  notes,
  highlights,
  notesView,
  onQuestionChange,
  onAsk,
  onOpenSettings,
  onOpenReaderPage,
  onSaveAnswerAsNote,
  onNotesViewChange,
}: AssistantRailProps) {
  const providerConfigured = providerSettings?.provider !== "none" && providerSettings?.api_key_configured;
  return (
    <aside className="assistant-rail" aria-label="Assistant">
      <header className="assistant-header">
        <h2>Assistant</h2>
        <p>{readerContext ? `Context: ${readerContext.paper.title} · ${readerContext.document.parse_status}` : "Context: no paper open"}</p>
      </header>
      {!providerConfigured ? (
        <section className="provider-callout">
          <strong>Model not configured</strong>
          <p>Configure a model provider to ask questions about the current paper.</p>
          <button type="button" onClick={onOpenSettings}>Configure model</button>
        </section>
      ) : null}
      <section className="assistant-card">
        <h3>Ask current paper</h3>
        <form className="ask-form" onSubmit={onAsk}>
          <label htmlFor="question">Question</label>
          <textarea id="question" value={question} onChange={(event) => onQuestionChange(event.target.value)} rows={4} />
          <button type="submit" disabled={!readerContext || question.trim().length === 0}>Ask</button>
        </form>
        {assistantProgress ? <p className="context-status">{assistantProgress}</p> : null}
      </section>
      {assistantAnswer ? (
        <article className="answer-block">
          <p>{assistantAnswer.answer}</p>
          <div className="answer-actions">
            <button type="button" onClick={onSaveAnswerAsNote}>Save answer as note</button>
          </div>
          <div className="citation-list">
            {assistantAnswer.citations.map((citation) => (
              <button aria-label={`Open citation page ${citation.page_number}`} className="citation-card" key={`${citation.chunk_id ?? "selection"}-${citation.page_number}-${citation.source_span}`} onClick={() => onOpenReaderPage(citation.page_number)} type="button">
                <strong>Page {citation.page_number}</strong>
                <p>{citation.snippet}</p>
              </button>
            ))}
          </div>
        </article>
      ) : null}
      <section className="notes-panel">
        <div className="segmented-control" aria-label="Notes and highlights">
          <button className={notesView === "notes" ? "active" : ""} onClick={() => onNotesViewChange("notes")} type="button">Notes</button>
          <button className={notesView === "highlights" ? "active" : ""} onClick={() => onNotesViewChange("highlights")} type="button">Highlights</button>
        </div>
        {notesView === "notes" ? (
          <div className="note-list">
            {notes.length === 0 ? <p className="empty compact">No notes saved for this paper.</p> : notes.map((note) => (
              <article className="note-item" key={note.id}>
                <strong>Note{note.page_number === null ? "" : ` Page ${note.page_number}`}</strong>
                <p>{note.body}</p>
              </article>
            ))}
          </div>
        ) : (
          <div className="note-list">
            {highlights.length === 0 ? <p className="empty compact">No highlights saved for this paper.</p> : highlights.map((highlight) => (
              <article className="note-item highlight-item" key={highlight.id}>
                <strong>Highlight Page {highlight.page_number}</strong>
                <p>{highlight.selected_text}</p>
              </article>
            ))}
          </div>
        )}
      </section>
    </aside>
  );
}
```

- [ ] **Step 4: Wire the shell in `App.tsx`**

In `apps/desktop/src/App.tsx`, add imports:

```tsx
import { AssistantRail } from "./components/AssistantRail";
import { LibraryRail } from "./components/LibraryRail";
import { ReaderWorkspace } from "./components/ReaderWorkspace";
import { TopBar } from "./components/TopBar";
```

Add state near existing state declarations:

```tsx
const [openSurface, setOpenSurface] = useState<"import" | "discover" | "jobs" | "settings" | null>(null);
const [searchPerformed, setSearchPerformed] = useState(false);
const [activePaperId, setActivePaperId] = useState<number | null>(null);
const [notesView, setNotesView] = useState<"notes" | "highlights">("notes");
```

In `handleSearch`, set `searchPerformed` to true before calling `searchLocal`:

```tsx
setSearchPerformed(true);
```

In `openPaper`, set active paper before loading context:

```tsx
setActivePaperId(paper.id);
```

When selecting a new library, reset:

```tsx
setOpenSurface(null);
setSearchPerformed(false);
setActivePaperId(null);
setNotesView("notes");
```

Replace the JSX returned from `return (` with this shell:

```tsx
return (
  <main className="app-shell">
    <TopBar
      backendStatus={backendStatus}
      paperCount={libraryStatus?.paper_count ?? papers.length}
      searchQuery={searchQuery}
      onSearchQueryChange={setSearchQuery}
      onSearchSubmit={() => {
        const form = new Event("submit", { bubbles: true, cancelable: true });
        document.getElementById("hidden-local-search-form")?.dispatchEvent(form);
      }}
      onOpenImport={() => setOpenSurface("import")}
      onOpenDiscover={() => setOpenSurface("discover")}
      onOpenJobs={() => setOpenSurface("jobs")}
      onOpenSettings={() => setOpenSurface("settings")}
      activeJobCount={recentJobs.filter((job) => job.status === "queued" || job.status === "running" || job.status === "failed").length}
    />
    <form id="hidden-local-search-form" hidden onSubmit={handleSearch} />
    <div className="workspace-grid">
      <LibraryRail
        papers={papers}
        activePaperId={activePaperId}
        favoriteFilter={favoriteFilter}
        tagFilter={tagFilter}
        tagInputs={tagInputs}
        searchHits={searchHits}
        searchPerformed={searchPerformed}
        onOpenPaper={openPaper}
        onToggleFavorite={handleToggleFavorite}
        onFavoriteFilterChange={(value) => {
          setFavoriteFilter(value);
          void refreshPapers({ favorite: value, tag: tagFilter });
        }}
        onTagFilterChange={setTagFilter}
        onApplyFilters={() => void refreshPapers()}
        onTagInputChange={(paperId, value) => setTagInputs((current) => ({ ...current, [paperId]: value }))}
        onAddTag={handleAddTag}
        onRemoveTag={handleRemoveTag}
        paperMetadata={paperMetadata}
        paperFromSearchHit={paperFromSearchHit}
      />
      <ReaderWorkspace
        readerContext={readerContext}
        activeReaderPage={activeReaderPage}
        selectedText={selectedText}
        selectedPageNumber={selectedPageNumber}
        selectionBusy={selectionBusy}
        pdfPreviewUrl={pdfPreviewUrl()}
        onOpenImport={() => setOpenSurface("import")}
        onOpenDiscover={() => setOpenSurface("discover")}
        onReaderPageMouseUp={handleReaderPageMouseUp}
        onSelectionAction={handleSelectionAction}
        onHighlightSelection={handleHighlightSelection}
        onSaveSelectionAsNote={handleSaveSelectionAsNote}
      />
      <AssistantRail
        readerContext={readerContext}
        providerSettings={providerSettings}
        question={question}
        assistantProgress={assistantProgress}
        assistantAnswer={assistantAnswer}
        notes={notes}
        highlights={highlights}
        notesView={notesView}
        onQuestionChange={setQuestion}
        onAsk={handleAsk}
        onOpenSettings={() => setOpenSurface("settings")}
        onOpenReaderPage={openReaderPage}
        onSaveAnswerAsNote={handleSaveAnswerAsNote}
        onNotesViewChange={setNotesView}
      />
    </div>
    {message ? <div className="toast-status" role="status">{message}</div> : null}
  </main>
);
```

- [ ] **Step 5: Add base CSS for shell**

Replace the top layout selectors in `apps/desktop/src/styles.css` with:

```css
:root {
  color: #1f2937;
  background: #eef2f7;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

body {
  margin: 0;
}

button,
input,
select,
textarea {
  font: inherit;
}

button {
  border-radius: 7px;
}

.app-shell {
  background: #eef2f7;
  color: #1f2937;
  min-height: 100vh;
}

.top-bar {
  align-items: center;
  background: #ffffff;
  border-bottom: 1px solid #d9e0ea;
  display: grid;
  gap: 16px;
  grid-template-columns: minmax(220px, 280px) minmax(280px, 1fr) auto;
  min-height: 72px;
  padding: 12px 20px;
}

.brand-block h1 {
  font-size: 18px;
  line-height: 1.2;
  margin: 0 0 6px;
}

.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.status-pill {
  background: #edf2f7;
  border: 1px solid #d9e0ea;
  border-radius: 999px;
  color: #475569;
  font-size: 12px;
  padding: 3px 8px;
}

.status-pill.ready {
  background: #e9f8ef;
  border-color: #b7e3c5;
  color: #166534;
}

.global-search input {
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-sizing: border-box;
  min-height: 40px;
  padding: 8px 12px;
  width: 100%;
}

.top-actions {
  display: flex;
  gap: 8px;
}

.top-actions button,
.onboarding-actions button,
.ask-form button,
.selection-toolbar button,
.compact-row button,
.tag-form button {
  background: #243044;
  border: 1px solid #243044;
  color: #ffffff;
  cursor: pointer;
  padding: 8px 11px;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(280px, 330px) minmax(520px, 1fr) minmax(300px, 360px);
  min-height: calc(100vh - 73px);
}

.library-rail,
.assistant-rail {
  background: #ffffff;
  min-width: 0;
  overflow: auto;
  padding: 16px;
}

.library-rail {
  border-right: 1px solid #d9e0ea;
}

.assistant-rail {
  border-left: 1px solid #d9e0ea;
}

.reader-workspace {
  min-width: 0;
  overflow: auto;
  padding: 20px;
}

.empty-reader {
  align-items: center;
  display: flex;
  justify-content: center;
}

.onboarding-panel {
  background: #ffffff;
  border: 1px solid #d9e0ea;
  border-radius: 8px;
  max-width: 620px;
  padding: 28px;
}

.onboarding-panel h2 {
  font-size: 24px;
  margin: 0 0 10px;
}

.eyebrow {
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  margin: 0 0 10px;
  text-transform: uppercase;
}

.onboarding-actions,
.compact-row,
.paper-card-actions {
  display: flex;
  gap: 8px;
}

.segmented-control {
  background: #edf2f7;
  border-radius: 8px;
  display: grid;
  gap: 4px;
  grid-template-columns: repeat(2, 1fr);
  padding: 4px;
}

.segmented-control button {
  background: transparent;
  border: 0;
  color: #475569;
  cursor: pointer;
  padding: 7px 9px;
}

.segmented-control button.active {
  background: #ffffff;
  color: #111827;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.12);
}
```

Keep existing form, paper, reader, answer, citation, and note selectors temporarily. Later tasks will replace them.

- [ ] **Step 6: Run shell test to verify GREEN**

Run from `apps/desktop`:

```powershell
npm test -- src/App.test.tsx -t "shows a reader-centered shell"
```

Expected: PASS.

- [ ] **Step 7: Run broader frontend tests**

Run from `apps/desktop`:

```powershell
npm test
```

Expected: Some old tests may fail because they still target always-visible forms. Keep failures limited to tests whose workflows are intentionally moving into dialogs/drawers. Do not commit if unrelated tests fail.

- [ ] **Step 8: Commit shell**

Run:

```powershell
git add apps/desktop/src/App.tsx apps/desktop/src/App.test.tsx apps/desktop/src/styles.css apps/desktop/src/components
git commit -m "feat: add reader-centered desktop shell"
```

### Task 2: Import Dialog

**Files:**
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Create: `apps/desktop/src/components/ImportDialog.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Replace PDF import test with dialog workflow**

Replace the existing `imports a PDF by source path` test with:

```tsx
it("imports a PDF from the import dialog", async () => {
  fetchMock
    .mockResolvedValueOnce(jsonResponse({ status: "ok", service: "knowledge-agent-backend" }))
    .mockResolvedValueOnce(jsonResponse(defaultLibraryStatus))
    .mockResolvedValueOnce(jsonResponse({ papers: [] }))
    .mockResolvedValueOnce(jsonResponse(defaultProviderSettings))
    .mockResolvedValueOnce(jsonResponse(emptyJobsResponse))
    .mockResolvedValueOnce(jsonResponse({ imported: true, paper: readerPaper, document: readerContextPayload.document }))
    .mockResolvedValueOnce(jsonResponse({ papers: [readerPaper] }));

  render(<App />);
  await userEvent.click(await screen.findByRole("button", { name: "Import" }));

  const dialog = screen.getByRole("dialog", { name: "Import papers" });
  await userEvent.type(screen.getByLabelText("PDF source path"), "F:\\papers\\example.pdf");
  await userEvent.click(within(dialog).getByRole("button", { name: "Import PDF" }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8765/api/imports/pdf",
      expect.objectContaining({ method: "POST" }),
    );
  });
  expect(fetchCallBody("/api/imports/pdf")).toEqual({ source_path: "F:\\papers\\example.pdf" });
  expect(await screen.findByText("PDF imported")).toBeInTheDocument();
  expect(screen.queryByRole("dialog", { name: "Import papers" })).not.toBeInTheDocument();
});
```

Add `within` to the Testing Library import:

```tsx
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
```

- [ ] **Step 2: Run PDF import dialog test to verify RED**

Run from `apps/desktop`:

```powershell
npm test -- src/App.test.tsx -t "imports a PDF from the import dialog"
```

Expected: FAIL because `ImportDialog` does not exist.

- [ ] **Step 3: Create `ImportDialog.tsx`**

Create `apps/desktop/src/components/ImportDialog.tsx`:

```tsx
import { FormEvent } from "react";

type ImportMode = "pdf" | "folder" | "bibliography";

type ImportDialogProps = {
  mode: ImportMode;
  sourcePath: string;
  folderPath: string;
  bibliographyPath: string;
  bibliographyFormat: string;
  exportPreview: string;
  onModeChange: (mode: ImportMode) => void;
  onSourcePathChange: (value: string) => void;
  onFolderPathChange: (value: string) => void;
  onBibliographyPathChange: (value: string) => void;
  onBibliographyFormatChange: (value: string) => void;
  onExportPreviewChange: (value: string) => void;
  onImportPdf: (event: FormEvent<HTMLFormElement>) => void;
  onImportFolder: (event: FormEvent<HTMLFormElement>) => void;
  onImportBibliography: (event: FormEvent<HTMLFormElement>) => void;
  onExportBibliography: (format: "bibtex" | "ris") => void;
  onClose: () => void;
};

export function ImportDialog({
  mode,
  sourcePath,
  folderPath,
  bibliographyPath,
  bibliographyFormat,
  exportPreview,
  onModeChange,
  onSourcePathChange,
  onFolderPathChange,
  onBibliographyPathChange,
  onBibliographyFormatChange,
  onExportPreviewChange,
  onImportPdf,
  onImportFolder,
  onImportBibliography,
  onExportBibliography,
  onClose,
}: ImportDialogProps) {
  return (
    <div className="modal-backdrop">
      <section aria-modal="true" className="modal-panel" role="dialog" aria-label="Import papers">
        <header className="modal-header">
          <div>
            <h2>Import papers</h2>
            <p>Add PDFs, folders, or bibliography metadata to the active library.</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close import dialog">Close</button>
        </header>
        <div className="segmented-control import-tabs" aria-label="Import mode">
          <button className={mode === "pdf" ? "active" : ""} type="button" onClick={() => onModeChange("pdf")}>PDF file</button>
          <button className={mode === "folder" ? "active" : ""} type="button" onClick={() => onModeChange("folder")}>Folder</button>
          <button className={mode === "bibliography" ? "active" : ""} type="button" onClick={() => onModeChange("bibliography")}>Bibliography</button>
        </div>
        {mode === "pdf" ? (
          <form className="dialog-form" onSubmit={onImportPdf}>
            <label htmlFor="source-path">PDF source path</label>
            <div className="compact-row">
              <input id="source-path" value={sourcePath} onChange={(event) => onSourcePathChange(event.target.value)} placeholder="F:\\papers\\example.pdf" />
              <button type="submit" disabled={sourcePath.trim().length === 0}>Import PDF</button>
            </div>
          </form>
        ) : null}
        {mode === "folder" ? (
          <form className="dialog-form" onSubmit={onImportFolder}>
            <label htmlFor="folder-path">PDF folder path</label>
            <div className="compact-row">
              <input id="folder-path" value={folderPath} onChange={(event) => onFolderPathChange(event.target.value)} placeholder="F:\\papers" />
              <button type="submit" disabled={folderPath.trim().length === 0}>Import folder</button>
            </div>
          </form>
        ) : null}
        {mode === "bibliography" ? (
          <form className="dialog-form" onSubmit={onImportBibliography}>
            <label htmlFor="bibliography-path">Bibliography source path</label>
            <input id="bibliography-path" value={bibliographyPath} onChange={(event) => onBibliographyPathChange(event.target.value)} placeholder="F:\\papers\\library.bib" />
            <label htmlFor="bibliography-format">Bibliography format</label>
            <div className="compact-row">
              <select id="bibliography-format" value={bibliographyFormat} onChange={(event) => onBibliographyFormatChange(event.target.value)}>
                <option value="auto">Auto</option>
                <option value="bibtex">BibTeX</option>
                <option value="ris">RIS</option>
              </select>
              <button type="submit" disabled={bibliographyPath.trim().length === 0}>Import bibliography</button>
            </div>
            <div className="secondary-actions">
              <button type="button" onClick={() => onExportBibliography("bibtex")}>Export BibTeX</button>
              <button type="button" onClick={() => onExportBibliography("ris")}>Export RIS</button>
            </div>
            <label htmlFor="bibliography-export-preview">Bibliography export preview</label>
            <textarea id="bibliography-export-preview" value={exportPreview} onChange={(event) => onExportPreviewChange(event.target.value)} rows={7} />
          </form>
        ) : null}
      </section>
    </div>
  );
}
```

- [ ] **Step 4: Wire import dialog**

In `App.tsx`, import:

```tsx
import { ImportDialog } from "./components/ImportDialog";
```

Add state:

```tsx
const [importMode, setImportMode] = useState<"pdf" | "folder" | "bibliography">("pdf");
```

Close the dialog after successful import in `handleImport`, `handleFolderImport`, and `handleBibliographyImport`:

```tsx
setOpenSurface(null);
```

Render after the workspace grid:

```tsx
{openSurface === "import" ? (
  <ImportDialog
    mode={importMode}
    sourcePath={sourcePath}
    folderPath={folderPath}
    bibliographyPath={bibliographyPath}
    bibliographyFormat={bibliographyFormat}
    exportPreview={exportPreview}
    onModeChange={setImportMode}
    onSourcePathChange={setSourcePath}
    onFolderPathChange={setFolderPath}
    onBibliographyPathChange={setBibliographyPath}
    onBibliographyFormatChange={setBibliographyFormat}
    onExportPreviewChange={setExportPreview}
    onImportPdf={handleImport}
    onImportFolder={handleFolderImport}
    onImportBibliography={handleBibliographyImport}
    onExportBibliography={handleBibliographyExport}
    onClose={() => setOpenSurface(null)}
  />
) : null}
```

- [ ] **Step 5: Add modal CSS**

Append to `styles.css`:

```css
.modal-backdrop {
  align-items: center;
  background: rgba(15, 23, 42, 0.38);
  display: flex;
  inset: 0;
  justify-content: center;
  position: fixed;
  z-index: 20;
}

.modal-panel {
  background: #ffffff;
  border: 1px solid #d9e0ea;
  border-radius: 8px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.22);
  box-sizing: border-box;
  max-height: calc(100vh - 64px);
  max-width: 760px;
  overflow: auto;
  padding: 20px;
  width: min(760px, calc(100vw - 48px));
}

.modal-header {
  align-items: flex-start;
  display: flex;
  gap: 16px;
  justify-content: space-between;
  margin-bottom: 16px;
}

.modal-header h2 {
  font-size: 20px;
  margin: 0 0 6px;
}

.modal-header p {
  color: #64748b;
  margin: 0;
}

.dialog-form {
  display: grid;
  gap: 10px;
  margin-top: 16px;
}

.dialog-form label {
  font-size: 13px;
  font-weight: 700;
}

.dialog-form input,
.dialog-form select,
.dialog-form textarea {
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  box-sizing: border-box;
  padding: 9px 10px;
  width: 100%;
}

.secondary-actions {
  display: flex;
  gap: 8px;
}
```

- [ ] **Step 6: Run import dialog test to verify GREEN**

Run from `apps/desktop`:

```powershell
npm test -- src/App.test.tsx -t "imports a PDF from the import dialog"
```

Expected: PASS.

- [ ] **Step 7: Update folder and bibliography tests**

Change existing folder and bibliography tests so they click `Import`, choose the correct import tab, and then fill the same labeled fields. Keep existing API body assertions.

Run:

```powershell
npm test -- src/App.test.tsx -t "folder import|bibliography"
```

Expected: PASS for folder and bibliography workflows.

- [ ] **Step 8: Commit import dialog**

Run:

```powershell
git add apps/desktop/src/App.tsx apps/desktop/src/App.test.tsx apps/desktop/src/styles.css apps/desktop/src/components/ImportDialog.tsx
git commit -m "feat: move imports into dialog"
```

### Task 3: Settings Dialog

**Files:**
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Create: `apps/desktop/src/components/SettingsDialog.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Update provider settings test**

Replace the first interaction lines in `saves provider settings without displaying the raw API key` with:

```tsx
render(<App />);
await userEvent.click(await screen.findByRole("button", { name: "Settings" }));
expect(screen.getByRole("dialog", { name: "Settings" })).toBeInTheDocument();
await userEvent.selectOptions(await screen.findByLabelText("Provider"), "openai_compatible");
await userEvent.type(screen.getByLabelText("Base URL"), "https://api.example.test/v1");
await userEvent.type(screen.getByLabelText("Proxy URL"), "http://127.0.0.1:7897");
await userEvent.type(screen.getByLabelText("Model"), "research-model");
await userEvent.type(screen.getByLabelText("API key"), "secret-key");
await userEvent.click(screen.getByRole("button", { name: "Save settings" }));
```

Add an assertion near the end:

```tsx
expect(screen.queryByRole("dialog", { name: "Settings" })).not.toBeInTheDocument();
```

- [ ] **Step 2: Run settings test to verify RED**

Run from `apps/desktop`:

```powershell
npm test -- src/App.test.tsx -t "saves provider settings"
```

Expected: FAIL because provider fields are not inside a settings dialog yet.

- [ ] **Step 3: Create `SettingsDialog.tsx`**

Create `apps/desktop/src/components/SettingsDialog.tsx`:

```tsx
import { FormEvent } from "react";

type SettingsDialogProps = {
  libraryPath: string;
  provider: string;
  baseUrl: string;
  model: string;
  proxyUrl: string;
  apiKey: string;
  outboundContextPolicy: string;
  apiKeyConfigured: boolean;
  onLibraryPathChange: (value: string) => void;
  onProviderChange: (value: string) => void;
  onBaseUrlChange: (value: string) => void;
  onModelChange: (value: string) => void;
  onProxyUrlChange: (value: string) => void;
  onApiKeyChange: (value: string) => void;
  onOutboundContextPolicyChange: (value: string) => void;
  onSelectLibrary: (event: FormEvent<HTMLFormElement>) => void;
  onSaveSettings: (event: FormEvent<HTMLFormElement>) => void;
  onClose: () => void;
};

export function SettingsDialog({
  libraryPath,
  provider,
  baseUrl,
  model,
  proxyUrl,
  apiKey,
  outboundContextPolicy,
  apiKeyConfigured,
  onLibraryPathChange,
  onProviderChange,
  onBaseUrlChange,
  onModelChange,
  onProxyUrlChange,
  onApiKeyChange,
  onOutboundContextPolicyChange,
  onSelectLibrary,
  onSaveSettings,
  onClose,
}: SettingsDialogProps) {
  return (
    <div className="modal-backdrop">
      <section aria-modal="true" className="modal-panel" role="dialog" aria-label="Settings">
        <header className="modal-header">
          <div>
            <h2>Settings</h2>
            <p>Configure the local library and model provider.</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close settings dialog">Close</button>
        </header>
        <form className="dialog-form settings-section" onSubmit={onSelectLibrary}>
          <h3>Library</h3>
          <label htmlFor="library-path">Library location</label>
          <div className="compact-row">
            <input id="library-path" value={libraryPath} onChange={(event) => onLibraryPathChange(event.target.value)} placeholder="F:\\KnowledgeAgentLibrary" />
            <button type="submit" disabled={libraryPath.trim().length === 0}>Select library</button>
          </div>
        </form>
        <form className="dialog-form settings-section" onSubmit={onSaveSettings}>
          <h3>Model provider</h3>
          <p className="context-status">{apiKeyConfigured ? "API key configured" : "API key not configured"}</p>
          <label htmlFor="provider">Provider</label>
          <select id="provider" value={provider} onChange={(event) => onProviderChange(event.target.value)}>
            <option value="none">None</option>
            <option value="openai_compatible">OpenAI-compatible</option>
            <option value="ollama">Ollama</option>
          </select>
          <label htmlFor="base-url">Base URL</label>
          <input id="base-url" value={baseUrl} onChange={(event) => onBaseUrlChange(event.target.value)} placeholder="https://api.example.com/v1" />
          <label htmlFor="model">Model</label>
          <input id="model" value={model} onChange={(event) => onModelChange(event.target.value)} placeholder="gpt-4.1-mini" />
          <label htmlFor="proxy-url">Proxy URL</label>
          <input id="proxy-url" value={proxyUrl} onChange={(event) => onProxyUrlChange(event.target.value)} placeholder="http://127.0.0.1:7897" />
          <label htmlFor="api-key">API key</label>
          <input id="api-key" value={apiKey} onChange={(event) => onApiKeyChange(event.target.value)} placeholder="Stored locally" type="password" />
          <label htmlFor="outbound-policy">Outbound policy</label>
          <select id="outbound-policy" value={outboundContextPolicy} onChange={(event) => onOutboundContextPolicyChange(event.target.value)}>
            <option value="snippets_only">Snippets only</option>
            <option value="local_only">Local only</option>
          </select>
          <button type="submit">Save settings</button>
        </form>
      </section>
    </div>
  );
}
```

- [ ] **Step 4: Wire settings dialog**

In `App.tsx`, import:

```tsx
import { SettingsDialog } from "./components/SettingsDialog";
```

Close settings after successful provider save in `handleSaveSettings`:

```tsx
setOpenSurface(null);
```

Render after `ImportDialog`:

```tsx
{openSurface === "settings" ? (
  <SettingsDialog
    libraryPath={libraryPath}
    provider={provider}
    baseUrl={baseUrl}
    model={model}
    proxyUrl={proxyUrl}
    apiKey={apiKey}
    outboundContextPolicy={outboundContextPolicy}
    apiKeyConfigured={providerSettings?.api_key_configured ?? false}
    onLibraryPathChange={setLibraryPath}
    onProviderChange={setProvider}
    onBaseUrlChange={setBaseUrl}
    onModelChange={setModel}
    onProxyUrlChange={setProxyUrl}
    onApiKeyChange={setApiKey}
    onOutboundContextPolicyChange={setOutboundContextPolicy}
    onSelectLibrary={handleSelectLibrary}
    onSaveSettings={handleSaveSettings}
    onClose={() => setOpenSurface(null)}
  />
) : null}
```

- [ ] **Step 5: Run settings test to verify GREEN**

Run from `apps/desktop`:

```powershell
npm test -- src/App.test.tsx -t "saves provider settings"
```

Expected: PASS.

- [ ] **Step 6: Commit settings dialog**

Run:

```powershell
git add apps/desktop/src/App.tsx apps/desktop/src/App.test.tsx apps/desktop/src/components/SettingsDialog.tsx
git commit -m "feat: move settings into dialog"
```

### Task 4: Discover Drawer

**Files:**
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Create: `apps/desktop/src/components/DiscoverDrawer.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Update external search test**

Change `searches external papers and displays open PDF availability` so it opens the drawer first:

```tsx
render(<App />);
await userEvent.click(await screen.findByRole("button", { name: "Discover" }));
expect(screen.getByRole("complementary", { name: "Discover literature" })).toBeInTheDocument();
await userEvent.type(screen.getByLabelText("External search"), "retrieval augmented generation");
await userEvent.click(screen.getByRole("button", { name: "Search external" }));
```

Keep the existing assertions for result title, source, and `Open PDF available`.

- [ ] **Step 2: Run discover test to verify RED**

Run from `apps/desktop`:

```powershell
npm test -- src/App.test.tsx -t "searches external papers"
```

Expected: FAIL because the discover drawer is not implemented.

- [ ] **Step 3: Create `DiscoverDrawer.tsx`**

Create `apps/desktop/src/components/DiscoverDrawer.tsx`:

```tsx
import { FormEvent } from "react";
import type { SearchResultRecord } from "../api";

type DiscoverDrawerProps = {
  externalQuery: string;
  externalResults: SearchResultRecord[];
  pendingDownloads: Record<number, string>;
  onExternalQueryChange: (value: string) => void;
  onExternalSearch: (event: FormEvent<HTMLFormElement>) => void;
  onDownloadOpenPdf: (result: SearchResultRecord) => void;
  onConfirmPendingImport: (result: SearchResultRecord) => void;
  onClose: () => void;
  resultMetadata: (result: SearchResultRecord) => string;
};

export function DiscoverDrawer({
  externalQuery,
  externalResults,
  pendingDownloads,
  onExternalQueryChange,
  onExternalSearch,
  onDownloadOpenPdf,
  onConfirmPendingImport,
  onClose,
  resultMetadata,
}: DiscoverDrawerProps) {
  return (
    <aside aria-label="Discover literature" className="drawer-panel">
      <header className="drawer-header">
        <div>
          <h2>Discover literature</h2>
          <p>Search external sources and import open PDFs into your local library.</p>
        </div>
        <button type="button" onClick={onClose} aria-label="Close discover drawer">Close</button>
      </header>
      <form className="drawer-form" onSubmit={onExternalSearch}>
        <label htmlFor="external-query">External search</label>
        <div className="compact-row">
          <input id="external-query" value={externalQuery} onChange={(event) => onExternalQueryChange(event.target.value)} placeholder="keyword, DOI, title, arXiv" />
          <button type="submit" disabled={externalQuery.trim().length === 0}>Search external</button>
        </div>
      </form>
      <div className="drawer-list">
        {externalResults.length === 0 ? (
          <p className="empty compact">Search external sources to find papers.</p>
        ) : (
          externalResults.map((result) => (
            <article className="result-card" key={result.id}>
              <span className="paper-title">{result.title}</span>
              <span className="paper-meta">{resultMetadata(result)}</span>
              <span className="source-label">{result.source}</span>
              {result.doi ? <span className="snippet">DOI {result.doi}</span> : null}
              {result.arxiv_id ? <span className="snippet">arXiv {result.arxiv_id}</span> : null}
              <span className={result.pdf_url ? "availability open" : "availability closed"}>
                {result.pdf_url ? "Open PDF available" : "Needs access"}
              </span>
              <div className="result-actions">
                {pendingDownloads[result.id] ? (
                  <button type="button" onClick={() => onConfirmPendingImport(result)}>Confirm import</button>
                ) : result.pdf_url ? (
                  <button type="button" onClick={() => onDownloadOpenPdf(result)}>Download PDF</button>
                ) : null}
              </div>
            </article>
          ))
        )}
      </div>
    </aside>
  );
}
```

- [ ] **Step 4: Wire discover drawer**

In `App.tsx`, import:

```tsx
import { DiscoverDrawer } from "./components/DiscoverDrawer";
```

Render after dialogs:

```tsx
{openSurface === "discover" ? (
  <DiscoverDrawer
    externalQuery={externalQuery}
    externalResults={externalResults}
    pendingDownloads={pendingDownloads}
    onExternalQueryChange={setExternalQuery}
    onExternalSearch={handleExternalSearch}
    onDownloadOpenPdf={handleDownloadOpenPdf}
    onConfirmPendingImport={handleConfirmPendingImport}
    onClose={() => setOpenSurface(null)}
    resultMetadata={resultMetadata}
  />
) : null}
```

- [ ] **Step 5: Add drawer CSS**

Append to `styles.css`:

```css
.drawer-panel {
  background: #ffffff;
  border-left: 1px solid #d9e0ea;
  box-shadow: -18px 0 42px rgba(15, 23, 42, 0.14);
  box-sizing: border-box;
  display: grid;
  gap: 14px;
  grid-template-rows: auto auto 1fr;
  height: 100vh;
  max-width: min(520px, 100vw);
  overflow: auto;
  padding: 20px;
  position: fixed;
  right: 0;
  top: 0;
  width: 520px;
  z-index: 18;
}

.drawer-header {
  align-items: flex-start;
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.drawer-header h2 {
  font-size: 20px;
  margin: 0 0 6px;
}

.drawer-header p,
.drawer-form label {
  color: #64748b;
  margin: 0;
}

.drawer-form {
  display: grid;
  gap: 8px;
}

.drawer-form input {
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  padding: 9px 10px;
}

.drawer-list {
  display: grid;
  gap: 10px;
}

.result-card {
  border: 1px solid #d9e0ea;
  border-radius: 8px;
  display: grid;
  gap: 7px;
  padding: 12px;
}
```

- [ ] **Step 6: Run discover tests to verify GREEN**

Run from `apps/desktop`:

```powershell
npm test -- src/App.test.tsx -t "external|download"
```

Expected: PASS for external discovery and open PDF import workflows.

- [ ] **Step 7: Commit discover drawer**

Run:

```powershell
git add apps/desktop/src/App.tsx apps/desktop/src/App.test.tsx apps/desktop/src/styles.css apps/desktop/src/components/DiscoverDrawer.tsx
git commit -m "feat: move discovery into drawer"
```

### Task 5: Jobs Drawer

**Files:**
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Create: `apps/desktop/src/components/JobsDrawer.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Update jobs tests**

Change `job panel queues a PDF folder import and refreshes job progress` so job details are not visible by default:

```tsx
render(<App />);
expect(await screen.findByRole("button", { name: "Jobs" })).toBeInTheDocument();
expect(screen.queryByText("No recent jobs.")).not.toBeInTheDocument();

await userEvent.click(screen.getByRole("button", { name: "Import" }));
await userEvent.click(screen.getByRole("button", { name: "Folder" }));
await userEvent.type(screen.getByLabelText("PDF folder path"), "F:\\incoming");
await userEvent.click(screen.getByRole("button", { name: "Import folder" }));

await userEvent.click(await screen.findByRole("button", { name: "Jobs 1" }));
expect(await screen.findByRole("complementary", { name: "Jobs" })).toBeInTheDocument();
expect(await screen.findByText("folder_import - succeeded")).toBeInTheDocument();
```

Update retry test to open `Jobs` before clicking `Retry job 7`.

- [ ] **Step 2: Run jobs tests to verify RED**

Run from `apps/desktop`:

```powershell
npm test -- src/App.test.tsx -t "job"
```

Expected: FAIL because the job drawer is not implemented.

- [ ] **Step 3: Create `JobsDrawer.tsx`**

Create `apps/desktop/src/components/JobsDrawer.tsx`:

```tsx
import type { Job } from "../api";

type JobsDrawerProps = {
  jobs: Job[];
  onRetryJob: (job: Job) => void;
  onClose: () => void;
};

export function JobsDrawer({ jobs, onRetryJob, onClose }: JobsDrawerProps) {
  return (
    <aside aria-label="Jobs" className="drawer-panel">
      <header className="drawer-header">
        <div>
          <h2>Jobs</h2>
          <p>Imports, downloads, and retries for the active library.</p>
        </div>
        <button type="button" onClick={onClose} aria-label="Close jobs drawer">Close</button>
      </header>
      <div className="drawer-list">
        {jobs.length === 0 ? (
          <p className="empty compact">No recent jobs.</p>
        ) : (
          jobs.map((job) => (
            <article className="job-card" key={job.id}>
              <strong>{job.kind} - {job.status}</strong>
              <span className="job-source">{job.source_path}</span>
              <span>{job.processed_items} / {job.total_items} processed</span>
              <span>{job.succeeded_items} succeeded, {job.failed_items} failed</span>
              {job.error ? <span className="job-error">{job.error}</span> : null}
              {job.status === "failed" ? (
                <button type="button" onClick={() => onRetryJob(job)} aria-label={`Retry job ${job.id}`}>Retry</button>
              ) : null}
            </article>
          ))
        )}
      </div>
    </aside>
  );
}
```

- [ ] **Step 4: Wire jobs drawer**

In `App.tsx`, import:

```tsx
import { JobsDrawer } from "./components/JobsDrawer";
```

Render after `DiscoverDrawer`:

```tsx
{openSurface === "jobs" ? (
  <JobsDrawer
    jobs={recentJobs}
    onRetryJob={handleRetryJob}
    onClose={() => setOpenSurface(null)}
  />
) : null}
```

- [ ] **Step 5: Add job card CSS**

Append to `styles.css`:

```css
.job-card {
  border: 1px solid #d9e0ea;
  border-radius: 8px;
  display: grid;
  gap: 6px;
  padding: 12px;
}

.job-card strong {
  font-size: 13px;
}

.job-card span {
  color: #475569;
  font-size: 12px;
  overflow-wrap: anywhere;
}

.job-error {
  color: #b91c1c;
}
```

- [ ] **Step 6: Run jobs tests to verify GREEN**

Run from `apps/desktop`:

```powershell
npm test -- src/App.test.tsx -t "job"
```

Expected: PASS.

- [ ] **Step 7: Commit jobs drawer**

Run:

```powershell
git add apps/desktop/src/App.tsx apps/desktop/src/App.test.tsx apps/desktop/src/styles.css apps/desktop/src/components/JobsDrawer.tsx
git commit -m "feat: move jobs into drawer"
```

### Task 6: Reader and Assistant Workflow Polish

**Files:**
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/components/ReaderWorkspace.tsx`
- Modify: `apps/desktop/src/components/AssistantRail.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Update reader open test**

Change `opens a paper and displays reader context for the assistant` expectations:

```tsx
expect(await screen.findByRole("heading", { name: "Reader Paper" })).toBeInTheDocument();
expect(await screen.findByText("parsed · 2 pages")).toBeInTheDocument();
expect(await screen.findByText("Context: Reader Paper · parsed")).toBeInTheDocument();
expect(screen.queryByText("No selection.")).not.toBeInTheDocument();
expect(screen.queryByRole("button", { name: "Translate selection" })).not.toBeInTheDocument();
```

- [ ] **Step 2: Update selection test**

Change `shows selected reader text in the assistant panel` to assert the contextual toolbar:

```tsx
expect(await screen.findByRole("toolbar", { name: "Selected text actions" })).toBeInTheDocument();
expect(screen.getByRole("button", { name: "Translate" })).toBeInTheDocument();
expect(screen.getByRole("button", { name: "Explain" })).toBeInTheDocument();
expect(screen.getByRole("button", { name: "Highlight" })).toBeInTheDocument();
expect(screen.getByRole("button", { name: "Note" })).toBeInTheDocument();
```

Update selected-text action tests to click `Translate`, `Explain`, `Highlight`, and `Note` instead of the old long button labels.

- [ ] **Step 3: Run reader workflow tests to verify RED**

Run from `apps/desktop`:

```powershell
npm test -- src/App.test.tsx -t "opens a paper|selected reader text|translates selected|explains selected|highlights selected|saves selected"
```

Expected: FAIL for tests still depending on old assistant selection panel labels.

- [ ] **Step 4: Implement final reader/assistant labels**

Ensure `ReaderWorkspace.tsx` uses:

```tsx
<button type="button" disabled={selectionBusy} onClick={() => onSelectionAction("translate")}>Translate</button>
<button type="button" disabled={selectionBusy} onClick={() => onSelectionAction("explain")}>Explain</button>
<button type="button" disabled={selectionBusy} onClick={onHighlightSelection}>Highlight</button>
<button type="button" disabled={selectionBusy} onClick={onSaveSelectionAsNote}>Note</button>
```

Ensure `AssistantRail.tsx` does not render `No selection.` or selection action buttons.

- [ ] **Step 5: Keep citation jump behavior**

In `AssistantRail.tsx`, citation buttons must keep:

```tsx
aria-label={`Open citation page ${citation.page_number}`}
onClick={() => onOpenReaderPage(citation.page_number)}
```

In `ReaderWorkspace.tsx`, page articles must keep:

```tsx
aria-current={activeReaderPage === page.page_number ? "page" : undefined}
id={`reader-page-${page.page_number}`}
```

- [ ] **Step 6: Run reader workflow tests to verify GREEN**

Run from `apps/desktop`:

```powershell
npm test -- src/App.test.tsx -t "opens a paper|selected reader text|translates selected|explains selected|highlights selected|saves selected|citation|streams current-paper|falls back"
```

Expected: PASS.

- [ ] **Step 7: Commit reader/assistant polish**

Run:

```powershell
git add apps/desktop/src/App.tsx apps/desktop/src/App.test.tsx apps/desktop/src/styles.css apps/desktop/src/components/ReaderWorkspace.tsx apps/desktop/src/components/AssistantRail.tsx
git commit -m "feat: polish reader assistant workflow"
```

### Task 7: Full Visual CSS Pass

**Files:**
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Replace legacy panel styles**

Remove or stop using legacy selectors for always-visible forms:

- `.sidebar`
- `.panel-form`
- `.jobs-section`
- `.library-section`
- `.assistant-panel`
- `.settings-form`
- `.selection-actions`

Keep selectors still referenced by the new components:

- `.paper-list`
- `.paper-open`
- `.paper-title`
- `.paper-meta`
- `.tag-list`
- `.tag-pill`
- `.tag-form`
- `.search-list`
- `.snippet`
- `.source-label`
- `.availability`
- `.result-actions`
- `.pdf-preview`
- `.extracted-text-layer`
- `.reader-page`
- `.answer-block`
- `.citation-list`
- `.note-list`
- `.note-item`
- `.highlight-item`

- [ ] **Step 2: Add card and rail polish CSS**

Ensure these selectors exist:

```css
.rail-header {
  align-items: flex-start;
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.rail-header h2,
.assistant-header h2 {
  font-size: 16px;
  margin: 0 0 4px;
}

.rail-header p,
.assistant-header p,
.context-status,
.empty {
  color: #64748b;
  margin: 0;
}

.tag-filter-form {
  display: grid;
  gap: 8px;
  margin: 12px 0;
}

.tag-filter-form label {
  font-size: 12px;
  font-weight: 800;
}

.paper-list,
.search-list,
.note-list {
  display: grid;
  gap: 10px;
}

.paper-card,
.search-result-card,
.citation-card,
.note-item {
  background: #ffffff;
  border: 1px solid #d9e0ea;
  border-radius: 8px;
  color: inherit;
  display: grid;
  gap: 8px;
  padding: 12px;
  text-align: left;
}

.paper-card.active {
  border-color: #2563eb;
  box-shadow: inset 3px 0 0 #2563eb;
}

.paper-open {
  background: transparent;
  border: 0;
  color: inherit;
  cursor: pointer;
  display: grid;
  gap: 5px;
  padding: 0;
  text-align: left;
  width: 100%;
}

.paper-title {
  color: #111827;
  font-weight: 800;
}

.paper-meta,
.snippet {
  color: #475569;
  font-size: 13px;
  line-height: 1.45;
}

.chip,
.tag-pill {
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  color: #334155;
  cursor: pointer;
  font-size: 12px;
  padding: 5px 8px;
}

.chip.active {
  background: #e9f8ef;
  border-color: #b7e3c5;
  color: #166534;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.reader-header {
  align-items: flex-start;
  display: flex;
  justify-content: space-between;
  margin-bottom: 14px;
}

.reader-header h2 {
  font-size: 22px;
  margin: 0 0 6px;
}

.reader-header p {
  color: #64748b;
  margin: 0;
}

.reader-grid {
  display: grid;
  gap: 14px;
}

.pdf-preview {
  background: #ffffff;
  border: 1px solid #d9e0ea;
  border-radius: 8px;
  box-sizing: border-box;
  min-height: 650px;
  width: 100%;
}

.extracted-text-layer {
  display: grid;
  gap: 10px;
}

.reader-page {
  background: #ffffff;
  border: 1px solid #d9e0ea;
  border-radius: 8px;
  padding: 16px;
}

.reader-page.active {
  border-color: #2563eb;
  box-shadow: inset 4px 0 0 #2563eb;
}

.selection-toolbar {
  align-items: center;
  background: #ffffff;
  border: 1px solid #d9e0ea;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  padding: 8px;
  position: sticky;
  top: 12px;
  z-index: 5;
}

.assistant-header {
  display: grid;
  gap: 4px;
}

.provider-callout,
.assistant-card,
.answer-block,
.notes-panel {
  border: 1px solid #d9e0ea;
  border-radius: 8px;
  display: grid;
  gap: 10px;
  padding: 12px;
}

.ask-form {
  display: grid;
  gap: 8px;
}

.ask-form label {
  font-size: 12px;
  font-weight: 800;
}

.ask-form textarea {
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  box-sizing: border-box;
  padding: 9px 10px;
  resize: vertical;
  width: 100%;
}

.citation-card {
  cursor: pointer;
  width: 100%;
}

.toast-status {
  background: #ffffff;
  border: 1px solid #d9e0ea;
  border-radius: 8px;
  bottom: 18px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.16);
  color: #334155;
  padding: 10px 12px;
  position: fixed;
  right: 18px;
  z-index: 30;
}
```

- [ ] **Step 3: Add responsive CSS**

Append:

```css
@media (max-width: 1180px) {
  .workspace-grid {
    grid-template-columns: minmax(260px, 320px) minmax(480px, 1fr);
  }

  .assistant-rail {
    grid-column: 1 / -1;
    border-left: 0;
    border-top: 1px solid #d9e0ea;
  }
}

@media (max-width: 860px) {
  .top-bar {
    grid-template-columns: 1fr;
  }

  .top-actions {
    flex-wrap: wrap;
  }

  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .library-rail,
  .assistant-rail {
    border-left: 0;
    border-right: 0;
  }

  .pdf-preview {
    min-height: 520px;
  }
}
```

- [ ] **Step 4: Run frontend tests and build**

Run from `apps/desktop`:

```powershell
npm test
npm run build
```

Expected: both PASS.

- [ ] **Step 5: Commit visual pass**

Run:

```powershell
git add apps/desktop/src/styles.css
git commit -m "style: refine desktop research workspace"
```

### Task 8: Visual Verification and README Screenshot Gate

**Files:**
- No source changes unless visual verification exposes a UI bug.

- [ ] **Step 1: Start demo backend**

Run from repository root with an ignored demo library:

```powershell
$env:KA_LIBRARY_DIR='F:\knowledge-agent\.local-library\readme-demo'
.\.venv\Scripts\python -m uvicorn knowledge_agent.main:app --host 127.0.0.1 --port 8765
```

Expected: backend starts and `/health` returns `{"status":"ok","service":"knowledge-agent-backend"}`.

- [ ] **Step 2: Import real demo PDF**

Run in another PowerShell:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/imports/pdf" -Method Post -ContentType "application/json" -Body (@{source_path="F:\knowledge-agent\2301.12652v4.pdf"} | ConvertTo-Json)
```

Expected: import succeeds and document parse status is `parsed`.

- [ ] **Step 3: Start Vite frontend**

Run from `apps/desktop`:

```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

Expected: Vite serves `http://127.0.0.1:5173`.

- [ ] **Step 4: Inspect desktop UI**

Open `http://127.0.0.1:5173` in a browser and verify:

- First screen shows top app bar, library rail, onboarding reader, and compact assistant callout.
- Import controls are not visible until `Import` is clicked.
- Provider settings are not visible until `Settings` is clicked.
- Jobs are not visible until `Jobs` is clicked.
- Discovery is not visible until `Discover` is clicked.
- Opening the paper gives visual priority to the PDF reader.
- No-selection state does not show disabled selection buttons.
- Selecting extracted text shows a contextual toolbar.
- Assistant citations appear as compact cards.

- [ ] **Step 5: Capture screenshots only after visual review**

After the UI passes the checklist, generate:

```text
docs/assets/screenshots/reader-assistant.png
docs/assets/screenshots/workbench.png
```

Do not commit screenshots if they show the old control-panel UI or stacked empty panels.

### Task 9: Final Verification

**Files:**
- Entire frontend and docs state.

- [ ] **Step 1: Run frontend verification**

Run from `apps/desktop`:

```powershell
npm test
npm run build
```

Expected: PASS.

- [ ] **Step 2: Run backend smoke tests**

Run from repository root:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
```

Expected: PASS. This guards against accidental API contract regressions.

- [ ] **Step 3: Run Rust verification**

Run from `apps/desktop/src-tauri`:

```powershell
cargo test --locked
cargo check --locked
```

Expected: PASS.

- [ ] **Step 4: Run hygiene checks**

Run from repository root:

```powershell
git diff --check
git grep -n -E 'sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----' -- README.md docs backend apps scripts
git ls-files | Select-String -Pattern '2301.12652v4.pdf|src-tauri/binaries|target/release/bundle|\.venv|node_modules|KnowledgeAgentLibrary|sk-[A-Za-z0-9]{20,}'
```

Expected: no whitespace errors, no real secret matches, no generated artifacts tracked.

- [ ] **Step 5: Commit final verification note if screenshots were regenerated**

If README screenshots are regenerated as part of this plan, commit them separately:

```powershell
git add docs/assets/screenshots README.md
git commit -m "docs: refresh readme screenshots"
```

If README screenshots are not regenerated in this plan, do not create a docs commit.

- [ ] **Step 6: Push**

Run:

```powershell
git push
```

Expected: branch updates on `origin/master`.

---

## Self-Review

Spec coverage:

- Top app bar: Task 1.
- Left library rail: Task 1 and Task 7.
- Reader workspace and onboarding: Task 1 and Task 6.
- Assistant rail: Task 1 and Task 6.
- Import dialog: Task 2.
- Settings dialog: Task 3.
- Discover drawer: Task 4.
- Jobs drawer: Task 5.
- Dynamic interactions: Tasks 2 through 6.
- Visual style: Task 7.
- Empty states: Tasks 1, 4, 5, and 6.
- Visual verification and screenshot gate: Task 8.
- Final verification: Task 9.

Known API constraint:

- The current `Paper` list API does not return per-paper parse status. This plan keeps parse status in the reader header after `reader-context` loads and does not add backend API fields.
