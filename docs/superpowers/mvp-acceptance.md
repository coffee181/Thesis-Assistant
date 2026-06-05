# Knowledge Agent MVP Acceptance Evidence

Date: 2026-06-05

This document maps the MVP acceptance criteria from `docs/superpowers/specs/2026-06-05-knowledge-agent-design.md` to implementation and test evidence. It is an evidence snapshot, not a new feature plan.

## Acceptance Matrix

| # | Criterion | Status | Product Evidence | Automated Test Evidence |
|---|---|---|---|---|
| 1 | Create or select a local managed library. | Accepted | Backend exposes `PUT /api/library` in `backend/src/knowledge_agent/main.py`; desktop exposes `Library location` and `Select library` in `apps/desktop/src/App.tsx`. | `backend/tests/test_api.py::test_select_library_switches_active_database`; `apps/desktop/src/App.test.tsx` test `selects a new library path and refreshes papers`. |
| 2 | Import a folder of PDFs and BibTeX/RIS metadata. | Accepted | Backend exposes folder import jobs and bibliography import/export endpoints in `backend/src/knowledge_agent/main.py`; desktop exposes `Import folder`, `Import bibliography`, and export controls in `apps/desktop/src/App.tsx`. | `backend/tests/test_api.py::test_folder_import_endpoint_creates_observable_job`; `backend/tests/test_api.py::test_import_bibliography_endpoint_imports_bib_file_and_lists_metadata`; `backend/tests/test_bibliography.py`; `apps/desktop/src/App.test.tsx` tests `job panel queues a PDF folder import and refreshes job progress` and `imports a bibliography file path and refreshes the library`. |
| 3 | Search the local library. | Accepted | Backend `GET /api/search/local` combines metadata/full-text hits with vector fallback; desktop `Search library` renders metadata and page hits. | `backend/tests/test_api.py::test_local_search_returns_page_snippet_hits`; `backend/tests/test_api.py::test_local_search_returns_metadata_only_hits`; `backend/tests/test_api.py::test_local_search_uses_semantic_vector_fallback`; `apps/desktop/src/App.test.tsx` test `searches the local library and displays page hits`. |
| 4 | Search external metadata sources by keyword, DOI, title, or arXiv ID. | Accepted | `ExternalDiscoveryClient` classifies and queries OpenAlex, Crossref, Semantic Scholar, arXiv, and Unpaywall; backend exposes `GET /api/search/external`; desktop exposes `External discovery`. | `backend/tests/test_discovery.py::test_classify_query_detects_doi_arxiv_and_keyword`; `backend/tests/test_discovery.py::test_external_discovery_client_queries_crossref_and_semantic_scholar`; `backend/tests/test_api.py::test_external_search_endpoint_returns_cached_candidates`; `apps/desktop/src/App.test.tsx` test `searches external papers and displays open PDF availability`. |
| 5 | Download an open-access PDF when available and confirm import. | Accepted | Backend downloads to `downloads/pending` through `POST /api/downloads/open-pdf` and imports only after `POST /api/imports/pending-download`; desktop shows `Download PDF` then `Confirm import`. | `backend/tests/test_api.py::test_download_open_pdf_then_confirm_imports_pending_file`; `backend/tests/test_api.py::test_download_open_pdf_requires_pdf_url`; `apps/desktop/src/App.test.tsx` test `downloads an open PDF result and confirms import into the library`. |
| 6 | Open a paper in the PDF reader. | Accepted with caveat | Backend exposes safe managed PDF streaming through `GET /api/papers/{paper_id}/pdf` and reader context through `GET /api/papers/{paper_id}/reader-context`; desktop opens an iframe PDF preview plus extracted text layer. | `backend/tests/test_api.py::test_reader_context_returns_current_paper_pages`; `backend/tests/test_api.py::test_paper_pdf_endpoint_streams_managed_pdf`; `apps/desktop/src/App.test.tsx` tests `opens a paper and displays reader context for the assistant` and `opens the managed PDF preview while keeping extracted text selectable`. |
| 7 | Select text and ask for Chinese translation or explanation. | Accepted | Desktop captures selected extracted text and calls `POST /api/papers/{paper_id}/assistant/selection` for translate and explain actions; backend prompts for Chinese translation/explanation while citing the selected source span. | `backend/tests/test_api.py::test_ask_selected_text_returns_selection_citation`; `backend/tests/test_assistant.py::test_selected_text_translation_sends_only_selection_to_provider`; `backend/tests/test_assistant.py::test_selected_text_explanation_uses_instruction`; `apps/desktop/src/App.test.tsx` tests `shows selected reader text in the assistant panel`, `translates selected text through the selected assistant endpoint`, and `explains selected text with the explain action`. |
| 8 | Ask a question about the current paper without manually copying text. | Accepted | Desktop ask flow automatically uses the active `readerContext.paper.id`; backend `answer_current_paper_question` retrieves current-paper chunks before calling the provider. Streaming endpoint returns progress events for the same flow. | `backend/tests/test_api.py::test_ask_current_paper_returns_traceable_answer`; `backend/tests/test_api.py::test_ask_current_paper_stream_returns_started_context_and_final_events`; `backend/tests/test_assistant.py::test_assistant_uses_current_paper_snippets_and_returns_citations`; `apps/desktop/src/App.test.tsx` test `streams current-paper ask progress before displaying the final answer`. |
| 9 | Receive an answer with page-level source citations and original snippets. | Accepted | Assistant answers include citation objects with `paper_id`, `title`, `page_number`, `snippet`, and `source_span`; desktop renders citation buttons that open cited pages. | `backend/tests/test_api.py::test_ask_current_paper_returns_traceable_answer`; `backend/tests/test_api.py::test_ask_current_paper_stream_returns_started_context_and_final_events`; `apps/desktop/src/App.test.tsx` test `opens a cited page from an assistant citation`. |
| 10 | Save a useful answer or selected passage as a note. | Accepted | Backend exposes `POST /api/notes` and per-paper note listing; desktop can save assistant answers and selected passages as notes. Highlights are also persisted. | `backend/tests/test_api.py::test_notes_and_highlights_endpoints_roundtrip`; `apps/desktop/src/App.test.tsx` tests `saves a selected assistant answer as a note`, `saves selected text directly as a note`, and `highlights selected text and displays it in the paper notes area`. |

## Real PDF Smoke Evidence

The project includes `scripts/smoke_real_pdf.py` for end-to-end local evidence using a real PDF and an OpenAI-compatible provider. It imports a local PDF into a temporary managed library, verifies extracted reader context, saves provider settings from environment variables, asks a current-paper question, and requires citations before returning success.

The latest known manual smoke run used local-only PDF input `F:\knowledge-agent\2301.12652v4.pdf`, provider model `glm-5.1`, and proxy `http://127.0.0.1:7897`. It reported 12 pages, 4 citations, provider `openai_compatible`, and a non-empty Chinese answer preview. API keys were supplied only through environment variables and are not recorded here.

## Baseline Caveats

These caveats are about implementation-route choices from the spec baseline, not blockers for the 10 MVP acceptance criteria.

- PDF rendering uses a browser PDF iframe plus selectable extracted text layer. The spec baseline named PDF.js through a React wrapper, which is not currently used.
- Selection works on the extracted text layer, not a true PDF.js text layer; source spans are page-level selection spans.
- Vector search uses `backend/src/knowledge_agent/vector_index.py`, a lightweight persistent local vector index under `indexes/vectors/`. The spec baseline named Chroma as the initial candidate, which is not currently used.
- First-run embedding setup is not implemented; provider settings cover chat providers and privacy policy, not embedding provider setup.
- Tauri can start the Python backend in development and supports an override backend command, but PyInstaller sidecar packaging is not implemented yet.
- Folder job progress is observable through `/api/jobs` polling. Assistant current-paper answers use server-sent events.
- Library selection and imports are path-input workflows. Native Windows folder/file pickers are not implemented yet.
- Traceable answers return citation objects with page and snippet evidence, but the backend does not validate that every model sentence contains an inline citation marker.

## Highest-Priority Polish After MVP

1. Replace the iframe PDF preview with a PDF.js/React viewer so selection, highlights, and citation navigation share one real PDF text layer.
2. Add first-run setup for native library selection, persisted library path, provider/privacy choices, and embedding setup.
3. Harden traceability by validating citation markers in model output and surfacing insufficient-evidence states more prominently.
4. Move open-access PDF download/import into background jobs with PDF validation, progress, retry, and clearer failure states.
5. Add the packaged Windows sidecar path after MVP behavior stays stable under real-paper smoke runs.

## Fresh Verification Snapshot

Fresh verification run on 2026-06-05 from `F:\knowledge-agent`:

| Command | Result |
|---|---|
| `.\.venv\Scripts\python -m pytest backend/tests -q` | Passed: 114 backend tests. One existing Starlette/httpx deprecation warning. |
| `npm test` from `apps/desktop` | Passed: 31 desktop tests. |
| `npm run build` from `apps/desktop` | Passed: TypeScript and Vite production build completed. |
| `cargo check --locked` from `apps/desktop/src-tauri` | Passed: Tauri Rust crate checked. |
| `.\.venv\Scripts\python .\scripts\smoke_real_pdf.py` with environment-only provider settings | Passed: imported `F:\knowledge-agent\2301.12652v4.pdf`, detected 12 pages, returned 4 citations, provider `openai_compatible`, non-empty Chinese answer preview. |

Smoke-test API keys were supplied only through process environment variables and are not recorded in this repository.
