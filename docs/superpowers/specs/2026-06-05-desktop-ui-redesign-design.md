# Desktop UI Redesign Design

## Goal

Redesign the desktop app UI so Thesis Assistant feels like a focused research workspace instead of an API control panel.

The redesign must preserve the existing MVP behavior while changing how the user reaches it: common reading and Q&A workflows stay visible, while low-frequency setup/import/export/provider controls move into dialogs, drawers, or compact menus.

## Problem Summary

The current UI exposes nearly every backend capability at once:

- Library path selection.
- Single PDF import.
- Folder import.
- Local search.
- External search.
- Bibliography import/export.
- Jobs.
- Library filters.
- Search results.
- External results.
- Selection tools.
- Model settings.
- Current-paper ask.
- Notes and highlights.

This makes the app look unfinished even when the backend works. The first viewport shows too many empty states, disabled buttons, plain forms, and low-frequency controls. The user cannot immediately see the core workflow: find or import a paper, read it, ask cited questions, and save notes.

## Design Direction

Use a reader-centered research workspace:

- A top app bar provides app identity, active library status, global search, import, discovery, jobs, and settings entry points.
- A left library rail shows papers, filters, tags, favorites, and local search results.
- The center reader owns the visual focus.
- A right assistant rail handles current-paper Q&A, citations, notes, and context status.
- Low-frequency controls live in modal dialogs or slide-out drawers.
- Empty states are task-oriented and should suggest the next action.

This is not a marketing redesign. It should feel like a quiet, utilitarian desktop research tool with enough polish for public screenshots.

## Layout

### Top App Bar

The app bar is always visible and contains:

- Product name: `Thesis Assistant`.
- Backend/library status as compact pills.
- Global search input with placeholder `Search library or paste DOI/title/arXiv`.
- Primary `Import` button.
- `Discover` button for external literature search.
- `Jobs` button with active/failed count when applicable.
- `Settings` button.

The top bar must replace always-visible library path forms, import path forms, external search forms, bibliography forms, and provider settings.

### Left Library Rail

The library rail is always visible on desktop and contains:

- Header with paper count and compact filter controls.
- Segmented filter: `All`, `Favorites`, `Recent`.
- Optional tag filter row using small chips.
- Paper cards.

Each paper card shows:

- Title.
- Authors/year or DOI fallback.
- Tags.
- Favorite indicator.
- Parse status.
- Small affordance for add/remove tags.

The rail should not show:

- Import path fields.
- Bibliography export preview.
- Jobs.
- External discovery results unless the discovery drawer is open.
- Multiple empty result sections at once.

### Center Reader

The reader is the main workspace.

When no paper is open, show a dashboard empty state with:

- A concise prompt to import or discover papers.
- Two primary actions: `Import papers` and `Discover literature`.
- A short local library summary.
- Optional recent papers if available.

When a paper is open, show:

- Reader header with title, metadata, parse status, and page count.
- Reader tabs or toggle: `PDF` and `Extracted text`.
- PDF preview as the default primary surface.
- Extracted text as a secondary pane or tab, not a full stacked duplicate below the PDF.
- Page navigation and citation jump state.

Selection behavior:

- Selecting extracted text opens a floating action toolbar near the selection or top of the reader.
- Toolbar actions: `Translate`, `Explain`, `Highlight`, `Note`.
- The right assistant rail may mirror the selected text, but should not show disabled selection buttons when there is no selection.

### Right Assistant Rail

The assistant rail is visible on desktop when there is enough width. It contains:

- Current paper context card.
- Ask composer.
- Streaming progress.
- Latest answer.
- Citation cards.
- Notes/highlights tabs.

The assistant rail should not show provider setup fields by default. If no provider is configured, show a compact callout with `Configure model`.

Citation cards must be compact but useful:

- Page number.
- Short snippet.
- Click action to navigate the reader.

Notes and highlights should be tabbed or collapsed so the ask composer and latest answer remain primary.

## Dialogs and Drawers

### Import Dialog

Opened from the top app bar `Import` button.

Tabs:

- `PDF file`
- `Folder`
- `Bibliography`

Fields:

- PDF path.
- Folder path.
- Bibliography path and format.

Actions:

- Import selected mode.
- Export BibTeX/RIS appears as secondary actions under the bibliography tab.

### Discover Drawer

Opened from the top app bar `Discover` button.

Contains:

- External query input.
- Source/status summary.
- Result cards with title, source, authors/year, DOI/arXiv, availability, and `Download PDF`/`Confirm import`.

The drawer should feel like a search workflow, not a permanent sidebar section.

### Jobs Drawer

Opened from the `Jobs` app bar button.

Contains:

- Recent import/download jobs.
- Progress summary.
- Failed job details.
- Retry action.

When no jobs exist, do not show the drawer automatically and do not show `No recent jobs` in the main interface.

### Settings Dialog

Opened from `Settings`.

Sections:

- Library location.
- Model provider.
- Base URL.
- Model.
- Proxy URL.
- API key.
- Outbound context policy.

API keys remain masked after save.

## Visual Style

The UI should be dense but organized:

- Use neutral surfaces with restrained contrast.
- Avoid a one-note dark slate palette.
- Use cards only for repeated items and bounded panels: paper cards, citation cards, notes, job items, result cards.
- Do not put cards inside cards.
- Use 6-8px radius.
- Use compact type scale suitable for desktop tools.
- Use icons for toolbar buttons where available; if no icon library is currently installed, implement the first redesign without adding one and leave icon adoption for a follow-up plan.
- Do not use hero-style text inside the application.
- Do not add decorative gradients, orbs, or illustration backgrounds.

Color should communicate state:

- Green for ready/imported/open PDF available.
- Amber for warnings or needs attention.
- Red for failures.
- Blue or neutral accent for active selection and citations.

## Interaction Requirements

The redesign must include dynamic behavior:

- Modal open/close for import and settings.
- Drawer open/close for discovery and jobs.
- Tabs for import mode and notes/highlights.
- Segmented filters in the library rail.
- Active paper selection state.
- Floating or contextual selected-text toolbar.
- Streaming assistant progress remains visible.
- Citation click scrolls/jumps to the cited page as existing behavior does.

## Empty States

Empty states must be meaningful and not stack together.

Examples:

- No papers: show onboarding in the center reader, not multiple empty lists.
- No current selection: hide selection tools instead of showing disabled buttons.
- No jobs: hide job content until Jobs is opened.
- No search hits: show inside the library rail only after the user has searched.
- No provider: show a compact assistant callout, not the full settings form.

## Scope

### In Scope

- Refactor the React UI structure.
- Rewrite CSS for the desktop workspace.
- Add modal/drawer/tabs/segmented-control state.
- Preserve all existing API calls and backend behavior.
- Update tests to cover the new UI workflow.
- Generate new README screenshots only after the redesigned UI passes visual review.

### Out of Scope

- Backend schema changes.
- New model provider behavior.
- New PDF rendering engine.
- Native file picker integration.
- Code signing.
- GitHub Release asset upload.

## Test Strategy

Frontend tests should move from asserting always-visible forms to asserting workflow entry points:

- Initial load shows app bar, library rail, reader onboarding, and assistant callout.
- Import dialog opens from `Import`, supports PDF/folder/bibliography flows, and closes after successful import.
- Settings dialog opens from `Settings`, saves provider settings, and never displays raw API key.
- Discover drawer opens from `Discover`, searches external sources, and supports open PDF download/import.
- Jobs drawer opens from `Jobs`, shows progress and retry.
- Opening a paper loads reader context and updates the assistant context.
- Selecting text reveals selected-text actions.
- Asking a question streams progress and displays citations.
- Clicking a citation jumps the reader to the cited page.

Use TDD for UI behavior changes.

## Visual Verification

After implementation:

- Run frontend tests and build.
- Start the local backend and Vite frontend with an ignored demo library.
- Import the real test PDF from `F:\knowledge-agent\2301.12652v4.pdf`.
- Capture desktop screenshots after opening a paper and producing a representative assistant answer or mocked answer state.
- Inspect screenshots before updating README.

The redesigned screenshot must not show:

- Empty stacked panels.
- Always-visible path forms.
- Full provider settings in the default assistant rail.
- Disabled selection buttons when nothing is selected.
- Multiple unrelated control groups competing with the reader.

## README Dependency

The open-source README polish is blocked on this redesign. README screenshots should be regenerated after the UI redesign, not from the current MVP control-panel UI.
