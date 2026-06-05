# Knowledge Agent

Knowledge Agent is a Windows-first local literature library and research assistant.

## Current Slice

This repository currently implements the local research assistant MVP slice:

- FastAPI backend health endpoint.
- SQLite managed library schema.
- PDF import by local path.
- Active managed library status and selection.
- Recursive folder PDF import.
- Hash-based duplicate detection.
- Basic paper listing API.
- BibTeX/RIS bibliography import and export.
- External literature discovery with open PDF download/import.
- Local full-text search over extracted PDF pages.
- Managed PDF preview with extracted text reader context.
- Current-paper assistant Q&A with page citations.
- Selected-text translation, explanation, and summarization.
- Notes and highlights for selected passages.
- OpenAI-compatible and Ollama provider settings, including optional provider proxy URL.
- React library shell.
- Minimal Tauri desktop wrapper.

The backend defaults to `%USERPROFILE%\KnowledgeAgentLibrary`, or `KA_LIBRARY_DIR` when set. In the desktop app, paste a managed library path into `Library location` to switch the active local library for the running backend.

## MVP Workflow

1. Start the backend and desktop app from the Development commands below.
2. Select a managed library path in `Library location`.
3. Import individual PDFs with `Import PDF`, or recursively import a folder with `Import folder`.
4. Import or export BibTeX/RIS metadata from the bibliography controls.
5. Search your local library with `Search library`.
6. Use `External search` to find papers by keyword, DOI, title, or arXiv ID, then `Download PDF` and `Confirm import` when an open PDF is available.
7. Open a paper from the library or search results. The reader shows the managed PDF preview and extracted text layer.
8. Select text in the extracted text layer to translate, explain, highlight, or save the selected passage as a note.
9. Ask questions in the assistant panel. Answers use current-paper snippets and return page-level citations.
10. Save useful assistant answers as notes in the paper notes area.

## Model Provider Settings

Set `Provider` to `OpenAI-compatible` or `Ollama` in the desktop `Model settings` panel.

For OpenAI-compatible gateways, `Base URL` can be the gateway root or an API-prefixed URL. A root URL is normalized to `/v1/chat/completions`, and a `/v1` URL is preserved. For example, both of these are valid:

```text
https://keungliang.dpdns.org/
https://keungliang.dpdns.org/v1
```

If your network needs a local proxy, set `Proxy URL`, for example:

```text
http://127.0.0.1:7897
```

API keys are stored in the local library database and are never returned by the settings API or displayed by the desktop app.

## Real PDF Smoke Test

Use the smoke script to verify a local PDF can be imported, parsed, and answered with current-paper citations through an OpenAI-compatible provider. The script reads secrets from environment variables and prints a short JSON summary.

```powershell
$env:KA_SMOKE_PDF='F:\knowledge-agent\2301.12652v4.pdf'
$env:KA_SMOKE_BASE_URL='https://keungliang.dpdns.org/'
$env:KA_SMOKE_MODEL='glm-5.1'
$env:KA_SMOKE_API_KEY='<your key>'
$env:KA_SMOKE_PROXY_URL='http://127.0.0.1:7897'
.\.venv\Scripts\python .\scripts\smoke_real_pdf.py
```

Omit `KA_SMOKE_LIBRARY_DIR` to use a temporary managed library. Set it only when you want to inspect the imported library after the smoke run.

## Development

Prerequisites:

- Python 3.13
- Node.js 24 and npm
- Rust and Cargo

Start the backend in one PowerShell window:

```powershell
.\scripts\dev-backend.ps1
```

Start the desktop app in another PowerShell window:

```powershell
.\scripts\dev-desktop.ps1
```

The backend listens on `http://127.0.0.1:8765`.

## Tests

Backend:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
```

Frontend:

```powershell
cd apps\desktop
npm test
npm run build
```
