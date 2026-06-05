# Knowledge Agent

Knowledge Agent is a Windows-first local literature library and research assistant.

## Current Slice

This repository currently implements the project foundation:

- FastAPI backend health endpoint.
- SQLite managed library schema.
- PDF import by local path.
- Hash-based duplicate detection.
- Basic paper listing API.
- React library shell.
- Minimal Tauri desktop wrapper.

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
