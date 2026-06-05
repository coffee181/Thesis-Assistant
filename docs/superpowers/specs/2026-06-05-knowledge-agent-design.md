# Knowledge Agent Design

## Summary

Knowledge Agent is a Windows-first desktop application for managing a local research literature library and reading papers with a traceable AI assistant. The first version focuses on a personal library of up to 10,000 PDFs, with local storage, local indexes, source-grounded question answering, translation, lightweight notes, and assisted discovery of open-access papers.

The application uses a hybrid model approach: source files, metadata, indexes, notes, highlights, and question-answer history stay local; model providers are configurable. Cloud LLM calls only receive the necessary snippets for explicit chat or translation tasks. Local providers such as Ollama are supported where practical.

## Goals

- Manage a local, application-owned literature library.
- Import PDFs, folders, BibTeX, and RIS files.
- Search for papers by keyword, DOI, title, or arXiv URL.
- Retrieve metadata from Crossref, arXiv, Semantic Scholar, and related public sources.
- Download open-access PDFs when available and require manual confirmation before adding them to the library.
- Provide a PDF reading interface with a right-side assistant.
- Let the assistant automatically use the current paper context during reading.
- Support selected-text translation, explanation, summarization, and follow-up questions.
- Require source-grounded answers by default, including paper, page, and original snippet.
- Support highlights, lightweight notes, saved Q&A notes, tags, and favorites.
- Keep the design Windows-first while avoiding unnecessary platform lock-in.

## Non-Goals

- Multi-user collaboration.
- Cloud library sync.
- Mobile apps.
- Zotero or Mendeley two-way sync.
- Complex knowledge graphs or Obsidian-style backlink editing.
- Circumventing publisher access controls or downloading non-open PDFs without user-provided access.
- Full automatic paper writing, submission, or peer-review workflows.
- Lab-scale collections with hundreds of thousands of documents.

## Product Shape

The first version is a desktop application, not a browser-only local web app. It should feel like a focused research workbench:

- Left area: library navigation, filters, tags, and search results.
- Center area: PDF reader.
- Right area: assistant panel for translation, explanation, traceable Q&A, and saved notes.

The reading layout prioritizes the PDF. The assistant operates beside the paper instead of replacing the paper as the primary workspace.

## Technical Architecture

Use Tauri, React, and a Python local backend.

### Tauri Desktop Shell

Tauri owns the Windows desktop application boundary:

- Application window and desktop packaging.
- Local filesystem permissions.
- Startup and shutdown of the Python backend.
- Basic settings integration.
- Future cross-platform packaging path.

### React Frontend

React owns the user interface:

- Library view.
- Search and discovery screens.
- PDF reader.
- Assistant panel.
- Notes, highlights, tags, and favorites.
- Settings for model providers, library path, proxy, and privacy options.

### Python Local Backend

Python owns research and indexing functionality:

- PDF parsing and text extraction.
- Metadata lookup and normalization.
- Open-access PDF discovery and download jobs.
- File hashing and deduplication.
- SQLite metadata persistence.
- Full-text indexing.
- Vector indexing.
- Retrieval-augmented generation.
- Translation and chat provider integrations.
- Background job execution and progress reporting.

The frontend communicates with the backend through localhost HTTP and WebSocket APIs. HTTP handles ordinary CRUD and command operations; WebSocket or server-sent events handle long-running job progress and assistant streaming.

## Local Library Management

The application owns a managed library directory. Imported PDFs are copied into this directory instead of being referenced only from their original location. This makes deduplication, backup, migration, metadata repair, and source tracing more reliable.

Example layout:

```text
KnowledgeAgentLibrary/
  papers/
    2024/
      smith-2024-rag-evaluation/
        paper.pdf
        metadata.json
        extracted-text.json
  notes/
    note-uuid.md
  exports/
  downloads/
    pending/
  indexes/
    fts/
    vectors/
  database.sqlite
```

File names should be normalized using available metadata such as first author, year, and title. The application also stores file hashes to detect duplicates even when filenames differ.

The app should preserve original PDFs. Highlights and notes are stored as application data with source spans instead of destructively editing PDFs in the first version.

## Data Model

SQLite is the canonical store for metadata and user-created data.

Core tables:

- `papers`: title, authors, year, DOI, arXiv ID, venue, abstract, status, canonical citation key.
- `documents`: file path, file hash, page count, parse status, import timestamps.
- `chunks`: paper ID, document ID, page number, section label, text, source span, embedding reference.
- `notes`: note body, linked paper, linked source span, created and updated timestamps.
- `highlights`: paper, page, source span, selected text, color, note link.
- `qna_entries`: question, answer, cited chunks, mode, provider, timestamps.
- `tags` and `paper_tags`: library organization.
- `search_results`: cached external search results before import.
- `jobs`: import, parse, index, search, and download task state.
- `settings`: model providers, privacy controls, library path, proxy, and defaults.

Indexes should be rebuildable from stored PDFs and extracted text. Loss of an index should not destroy metadata, notes, or source traceability.

## Search and Discovery

The app supports two search modes:

1. Local search across the user's managed library.
2. External discovery for finding new papers.

Local search combines structured filters, keyword search, and semantic search. Structured filters include author, year, venue, tag, favorite status, and import status. Keyword search uses full-text indexing. Semantic search uses vector retrieval over extracted chunks.

External discovery supports:

- Keywords.
- DOI.
- Title.
- arXiv URL or ID.

Candidate metadata comes from sources such as Crossref, arXiv, Semantic Scholar, and Unpaywall. Results are merged and deduplicated. When an open-access PDF is available, the app can download it to a pending area and ask the user to confirm import. If no open PDF is available, the app saves metadata and source links with a "needs access" state.

## PDF Reading and Assistant Interaction

The reading screen uses the PDF as the main view and the assistant as a right-side panel.

Assistant context assembly follows this priority:

1. If the user selected text, use the selected span plus nearby context.
2. If there is no selection, use the current page and current section when available.
3. If the question is broader, retrieve relevant chunks from the current paper first.
4. Only search across the whole library when the user asks for cross-paper or library-wide analysis.

The assistant supports:

- Translating selected text into Chinese.
- Explaining methods, terms, equations, figures, and claims.
- Summarizing a page, section, or paper.
- Answering questions about the current paper.
- Comparing the current paper with other library papers when requested.
- Saving useful answers as notes.

The default interaction language is Chinese. Original English snippets are kept in citations and can be shown alongside Chinese explanations.

## Traceability and Answer Modes

The default mode is strict traceable answering:

- Important claims must cite source paper, page, and original snippet.
- The UI should make cited snippets easy to open in the PDF.
- If the library does not contain enough evidence, the assistant must say so.
- The assistant must not fabricate citations.

A separate free reasoning or brainstorming mode may exist, but it must be clearly marked as not evidence-backed. This prevents casual reasoning from being confused with source-grounded literature answers.

## Model Providers and Privacy

The app uses a hybrid provider model.

Local-first behavior:

- PDFs, extracted text, metadata, notes, highlights, indexes, and Q&A history stay local.
- Full-document indexing and retrieval are local.
- Embeddings should support local providers such as Ollama-compatible models where available.

Cloud-capable behavior:

- OpenAI-compatible chat providers can be configured.
- Cloud LLM calls are only made when the user explicitly asks for translation, explanation, summarization, or Q&A.
- Cloud calls send only the selected or retrieved snippets required for the current task, not the entire library.
- Settings should make provider selection, API keys, proxy, and outbound-context policy explicit.

The first version should include enough settings to let a user choose between local-only and hybrid use.

## Notes and Highlights

The first version includes lightweight knowledge capture:

- PDF text highlights.
- Notes attached to selected text, pages, or papers.
- Saving assistant answers as notes.
- Tags and favorites.
- Per-paper note review.

It does not include a full block editor, collaborative editing, or a complex backlink graph.

## Background Jobs

Long-running work is handled as observable background jobs:

- Import PDFs.
- Parse documents.
- Fetch metadata.
- Download open PDFs.
- Build or rebuild full-text indexes.
- Build or rebuild vector indexes.

The UI should show progress, failure states, retry actions, and enough detail for users to understand what happened. Failed jobs must not corrupt the library.

## Error Handling

Expected error cases:

- PDF parsing fails or produces poor text.
- Metadata lookup returns conflicting records.
- A paper has no DOI.
- Download source is unavailable.
- Duplicate import is detected.
- Model provider is not configured or fails.
- Cloud request is blocked by network or proxy settings.
- Vector index is missing or stale.

The app should preserve user data and expose recoverable states. For example, a paper can be imported even if metadata lookup fails; metadata can be edited later. If indexing fails, the PDF still remains in the library and the job can be retried.

## Testing Strategy

The implementation should include focused automated tests around the risky boundaries:

- Metadata normalization and deduplication.
- PDF import and hash-based duplicate detection.
- Chunk source spans and page references.
- Retrieval context assembly for selected text, current page, current paper, and cross-library queries.
- Traceable answer formatting.
- Provider routing and privacy policy enforcement.
- Job state transitions.

UI tests should cover the main workflows:

- Import a PDF.
- Search local library.
- Open a paper.
- Ask a question with current paper context.
- Verify citations link back to source pages.
- Save an assistant answer as a note.

## MVP Acceptance Criteria

The MVP is successful when a Windows user can:

1. Create or select a local managed library.
2. Import a folder of PDFs and BibTeX/RIS metadata.
3. Search the local library.
4. Search external metadata sources by keyword, DOI, title, or arXiv ID.
5. Download an open-access PDF when available and confirm import.
6. Open a paper in the PDF reader.
7. Select text and ask for Chinese translation or explanation.
8. Ask a question about the current paper without manually copying text.
9. Receive an answer with page-level source citations and original snippets.
10. Save a useful answer or selected passage as a note.

## Baseline Implementation Decisions

The implementation plan should start from these baseline choices unless a concrete blocker appears:

- PDF rendering: PDF.js through a React PDF viewer wrapper.
- Python API framework: FastAPI with streaming support for assistant responses and job progress.
- Local metadata store: SQLite with FTS5 enabled.
- Local vector store: a persistent local vector database under `indexes/vectors/`, with stored chunk IDs that map back to SQLite source spans. Chroma is the initial candidate because it is Python-native and simple to persist locally.
- Backend packaging: package the Python backend as a Tauri sidecar process, initially via PyInstaller, and have the Tauri shell start it on a localhost port.
- Embedding setup: ask during first-run setup. Prefer a local provider such as Ollama when available; otherwise leave embeddings disabled until the user configures either local or cloud embeddings.

These choices preserve local data ownership, source traceability, and the PDF-centered reading workflow while keeping the first implementation path concrete.
