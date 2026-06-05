$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  python -m venv .venv
}

.\.venv\Scripts\python -m pip install -e "backend[dev]"

$env:KA_LIBRARY_DIR = Join-Path (Get-Location) ".local-library"
.\.venv\Scripts\python -m uvicorn knowledge_agent.main:app --host 127.0.0.1 --port 8765 --reload
