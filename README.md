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
- PDF text reader context.
- Current-paper assistant Q&A with page citations.
- Selected-text translation, explanation, and summarization.
- Notes and highlights for selected passages.
- OpenAI-compatible and Ollama provider settings.
- React library shell.
- Minimal Tauri desktop wrapper.

The backend defaults to `%USERPROFILE%\KnowledgeAgentLibrary`, or `KA_LIBRARY_DIR` when set. In the desktop app, paste a managed library path into `Library location` to switch the active local library for the running backend.

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
