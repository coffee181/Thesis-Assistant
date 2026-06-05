# Citation Page Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let assistant citations open the cited page in the reader so traceable answers are easier to verify.

**Architecture:** Keep the current iframe PDF preview plus extracted text reader. Add a reader page target state in `App.tsx`; citations become buttons that set the active page, update the PDF iframe URL with `#page=<n>`, and scroll the extracted text page into view.

**Tech Stack:** React 18, TypeScript, Vitest, Testing Library, Vite.

---

## Scope

This plan implements:

- Stable DOM anchors for extracted text pages.
- PDF iframe page fragment updates when a cited page is opened.
- Assistant citation buttons that navigate to their source page.
- A visible active-page state on the extracted text layer.
- Focused frontend tests for citation page navigation.

This plan does not implement PDF.js rendering, text-coordinate highlights, page thumbnails, backend changes, or citation snippet matching.

## File Structure

Modify:

```text
apps/desktop/src/App.tsx
apps/desktop/src/App.test.tsx
apps/desktop/src/styles.css
docs/superpowers/plans/2026-06-05-citation-page-navigation-plan.md
```

Responsibilities:

- `App.tsx`: Manage active reader page, construct PDF preview URL, and handle citation page navigation.
- `App.test.tsx`: Prove clicking a citation changes the PDF URL and marks the cited extracted-text page active.
- `styles.css`: Style clickable citations and active reader pages.

## Task 1: Citation Page Navigation

**Files:**

- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Write failing frontend test**

Add a test near the existing assistant Q&A test:

```tsx
it("opens a cited page from an assistant citation", async () => {
  // Queue initial app load, reader context, notes/highlights, and ask response.
  // Ask a question that returns a citation for page 2.
  // Click the citation button.
  // Assert the PDF iframe src ends with `/api/papers/1/pdf#page=2`.
  // Assert the extracted text page 2 article has `aria-current="page"`.
});
```

Run:

```powershell
cd apps\desktop
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'
npm test -- --runInBand
```

Expected: FAIL because citations are static `<div>` elements and the PDF URL has no page fragment.

- [ ] **Step 2: Implement page navigation**

In `App.tsx`:

- Add state:

```tsx
const [activeReaderPage, setActiveReaderPage] = useState<number | null>(null);
```

- Clear the active page when selecting a new library or opening a paper.
- Add:

```tsx
function pdfPreviewUrl(): string {
  if (!readerContext) return "";
  const baseUrl = paperPdfUrl(readerContext.paper.id);
  return activeReaderPage === null ? baseUrl : `${baseUrl}#page=${activeReaderPage}`;
}

function openReaderPage(pageNumber: number) {
  setActiveReaderPage(pageNumber);
  window.requestAnimationFrame(() => {
    document
      .getElementById(`reader-page-${pageNumber}`)
      ?.scrollIntoView({ block: "start" });
  });
}
```

- Use `pdfPreviewUrl()` for the iframe `src`.
- Add `id`, `aria-current`, and active class to page articles.
- Render citations as `<button type="button">` with `onClick={() => openReaderPage(citation.page_number)}`.

- [ ] **Step 3: Style citation/page active states**

In `styles.css`:

```css
.reader-page.active {
  border-color: #2563eb;
  box-shadow: inset 4px 0 0 #2563eb;
}

.citation {
  cursor: pointer;
  text-align: left;
  width: 100%;
}

.citation:focus-visible {
  outline: 3px solid #93c5fd;
  outline-offset: 2px;
}
```

- [ ] **Step 4: Verify frontend tests pass**

Run:

```powershell
cd apps\desktop
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'
npm test
```

Expected: PASS.

- [ ] **Step 5: Run build**

Run:

```powershell
cd apps\desktop
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'
npm run build
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add apps/desktop/src/App.tsx apps/desktop/src/App.test.tsx apps/desktop/src/styles.css docs/superpowers/plans/2026-06-05-citation-page-navigation-plan.md
git commit -m "feat: open cited pages in reader"
```

## Self-Review Notes

- Spec coverage: Covers the traceability requirement that cited snippets are easy to open in the PDF/reader.
- Placeholder scan: No TBD/TODO placeholders remain.
- Type consistency: Uses existing `Citation.page_number`; no API response changes.
