# Selected Passage Note Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a reader save the currently selected passage directly as a local note without first asking the assistant.

**Architecture:** Reuse the existing `POST /api/notes` backend and desktop `createNote` API client. Add one focused frontend workflow beside the existing selected-text actions: when reader text is selected, clicking `Save selection as note` posts a `note_type: "selection"` note and prepends it to the current paper notes list.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, existing FastAPI note endpoint.

---

## Scope

This plan implements:

- A desktop button for saving the selected reader passage as a note.
- A frontend test proving the request body includes the current paper, page number, source span, selected text, `note_type: "selection"`, and `qna_id: null`.
- Immediate display of the saved selection in the current paper notes list.

This plan does not implement backend changes, manual note editing, tags, favorites, PDF coordinate annotations, or rich text notes.

## File Structure

Modify:

```text
apps/
  desktop/
    src/
      App.test.tsx
      App.tsx
docs/
  superpowers/plans/2026-06-05-selected-passage-note-plan.md
```

Responsibilities:

- `apps/desktop/src/App.test.tsx`: Add the TDD coverage for saving a selected passage as a note.
- `apps/desktop/src/App.tsx`: Add the click handler and button using the existing `createNote` client.

## Task 1: Desktop Selected Passage Note Workflow

**Files:**
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`

- [ ] **Step 1: Write the failing frontend test**

Add this test near the existing selected-text note/highlight tests in `apps/desktop/src/App.test.tsx`:

```tsx
it("saves selected text directly as a note", async () => {
  queueInitialReaderLoad();
  queueOpenReaderContext();
  fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      id: 32,
      paper_id: 1,
      body: "retrieval augmented generation",
      page_number: 2,
      source_span: "page:2:selection",
      selected_text: "retrieval augmented generation",
      note_type: "selection",
      qna_id: null,
      created_at: "now",
      updated_at: "now",
    }),
  });

  await openReaderPaper();
  selectReaderText("retrieval augmented generation");
  await userEvent.click(await screen.findByRole("button", { name: "Save selection as note" }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8765/api/notes",
      expect.objectContaining({ method: "POST" }),
    );
  });
  expect(fetchCallBody("/api/notes")).toMatchObject({
    paper_id: 1,
    body: "retrieval augmented generation",
    page_number: 2,
    source_span: "page:2:selection",
    selected_text: "retrieval augmented generation",
    note_type: "selection",
    qna_id: null,
  });
  expect(await screen.findByText("Note Page 2")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test -- -t "saves selected text directly as a note"
```

Expected: FAIL because the `Save selection as note` button does not exist.

- [ ] **Step 3: Implement the minimal desktop UI**

Add this handler in `apps/desktop/src/App.tsx` near `handleHighlightSelection`:

```tsx
async function handleSaveSelectionAsNote() {
  if (!readerContext || !selectedText.trim() || selectedPageNumber === null) return;
  setMessage("");
  setSelectionBusy(true);
  try {
    const note = await createNote({
      paper_id: readerContext.paper.id,
      body: selectedText,
      page_number: selectedPageNumber,
      source_span: selectedSourceSpan,
      selected_text: selectedText,
      note_type: "selection",
      qna_id: null,
    });
    setNotes((current) => [note, ...current]);
    setMessage("Selection note saved");
  } catch (error) {
    setMessage(error instanceof Error ? error.message : "Selection note save failed");
  } finally {
    setSelectionBusy(false);
  }
}
```

Add this button in the existing `.selection-actions` group:

```tsx
<button
  type="button"
  disabled={!selectionReady || selectionBusy}
  onClick={handleSaveSelectionAsNote}
>
  Save selection as note
</button>
```

- [ ] **Step 4: Run the frontend tests**

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
```

Expected: PASS.

- [ ] **Step 5: Run final verification**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm run build
```

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

```powershell
git add docs/superpowers/plans/2026-06-05-selected-passage-note-plan.md apps/desktop/src/App.test.tsx apps/desktop/src/App.tsx
git commit -m "feat: save selected passages as notes"
```

## Self-Review Notes

- Spec coverage: This directly closes MVP acceptance criterion 10 for saving a selected passage as a note.
- Placeholder scan: No placeholder, TBD, or deferred implementation text remains.
- Type consistency: The plan uses the existing `CreateNoteRequest` fields from `apps/desktop/src/api.ts`.
