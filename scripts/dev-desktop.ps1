$ErrorActionPreference = "Stop"

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
