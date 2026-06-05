$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  python -m venv .venv
}

.\.venv\Scripts\python -m pip install -e "backend[dev]"

Push-Location apps\desktop
try {
  if (-not (Test-Path ".\node_modules")) {
    npm install
  }
  npm run tauri -- dev
}
finally {
  Pop-Location
}
