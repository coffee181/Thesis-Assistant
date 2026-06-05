$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$desktopDir = Join-Path $repoRoot "apps\desktop"
$tauriDir = Join-Path $desktopDir "src-tauri"
$backendBinaryDir = Join-Path $tauriDir "binaries"
$backendBinaryName = "knowledge-agent-backend-x86_64-pc-windows-msvc"
$backendBinaryPath = Join-Path $backendBinaryDir "$backendBinaryName.exe"
$pyinstallerWork = Join-Path $repoRoot "release\pyinstaller-work"
$pyinstallerSpec = Join-Path $repoRoot "release\pyinstaller-spec"

function Write-Section([string] $Message) {
  Write-Host ""
  Write-Host "==> $Message"
}

function Require-Command([string] $Name, [string] $InstallHint) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "$Name was not found. $InstallHint"
  }
}

Write-Section "Checking release prerequisites"
Require-Command "python" "Install Python 3.13 and make sure python.exe is on PATH."
Require-Command "npm" "Install Node.js and npm."
Require-Command "cargo" "Install Rust and Cargo."

Write-Section "Preparing Python virtual environment"
if (-not (Test-Path $venvPython)) {
  python -m venv (Join-Path $repoRoot ".venv")
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e "$repoRoot\backend[dev]" pyinstaller

Write-Section "Building backend executable"
New-Item -ItemType Directory -Force -Path $backendBinaryDir | Out-Null
if (Test-Path $backendBinaryPath) {
  Remove-Item -LiteralPath $backendBinaryPath -Force
}
New-Item -ItemType Directory -Force -Path $pyinstallerWork | Out-Null
New-Item -ItemType Directory -Force -Path $pyinstallerSpec | Out-Null

& $venvPython -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --name $backendBinaryName `
  --distpath $backendBinaryDir `
  --workpath $pyinstallerWork `
  --specpath $pyinstallerSpec `
  --paths (Join-Path $repoRoot "backend\src") `
  --collect-submodules "uvicorn" `
  --collect-submodules "httptools" `
  --collect-submodules "websockets" `
  (Join-Path $repoRoot "backend\src\knowledge_agent\server.py")

if (-not (Test-Path $backendBinaryPath)) {
  throw "Backend executable was not created at $backendBinaryPath"
}

Write-Section "Smoke testing backend executable"
$backendProcess = Start-Process `
  -FilePath $backendBinaryPath `
  -ArgumentList @("--host", "127.0.0.1", "--port", "8765") `
  -PassThru `
  -WindowStyle Hidden
try {
  $health = $null
  for ($attempt = 0; $attempt -lt 30; $attempt += 1) {
    try {
      $health = Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -TimeoutSec 2
      break
    }
    catch {
      Start-Sleep -Milliseconds 500
    }
  }
  if ($null -eq $health -or $health.status -ne "ok" -or $health.service -ne "knowledge-agent-backend") {
    throw "Backend executable health check failed"
  }
}
finally {
  if ($backendProcess -and -not $backendProcess.HasExited) {
    Stop-Process -Id $backendProcess.Id -Force
    $backendProcess.WaitForExit()
  }
}

Write-Section "Preparing desktop dependencies"
Push-Location $desktopDir
try {
  if (-not (Test-Path ".\node_modules")) {
    npm install
  }

  Write-Section "Building Tauri NSIS installer"
  npm run tauri -- build --bundles nsis --config src-tauri/tauri.release.conf.json
}
finally {
  Pop-Location
}

Write-Section "Release artifacts"
$nsisDir = Join-Path $tauriDir "target\release\bundle\nsis"
$installers = @()
if (Test-Path $nsisDir) {
  $installers = @(Get-ChildItem -LiteralPath $nsisDir -Filter "*.exe" -File)
}
if ($installers.Count -eq 0) {
  throw "No NSIS installer was produced under $nsisDir"
}

foreach ($installer in $installers) {
  $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $installer.FullName
  Write-Host $installer.FullName
  Write-Host "SHA256 $($hash.Hash)"
}
