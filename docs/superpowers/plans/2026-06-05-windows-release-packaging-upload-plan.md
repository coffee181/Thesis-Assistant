# Windows Release Packaging and Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows installer with a bundled Python backend and push the source release packaging work to `https://github.com/coffee181/Thesis-Assistant.git`.

**Architecture:** Add a PyInstaller-compatible backend entrypoint, teach the Tauri launcher to prefer a bundled backend binary in release builds while preserving development `.venv` startup, add a repeatable PowerShell release script, and document private sharing. Generated binaries and installers stay ignored and uncommitted.

**Tech Stack:** Python 3.13, PyInstaller, FastAPI/Uvicorn, Rust/Tauri v2, PowerShell, Git over HTTPS proxy `127.0.0.1:7897`.

---

### Task 1: Backend Release Entrypoint

**Files:**
- Create: `backend/src/knowledge_agent/server.py`
- Test: `backend/tests/test_server.py`

- [x] **Step 1: Write failing server argument tests**

Create `backend/tests/test_server.py`:

```python
from knowledge_agent.server import parse_args


def test_parse_args_defaults_to_localhost_port():
    args = parse_args([])

    assert args.host == "127.0.0.1"
    assert args.port == 8765


def test_parse_args_accepts_host_and_port():
    args = parse_args(["--host", "127.0.0.2", "--port", "9000"])

    assert args.host == "127.0.0.2"
    assert args.port == 9000
```

- [x] **Step 2: Run tests to verify RED**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_server.py -q
```

Expected: FAIL because `knowledge_agent.server` does not exist.

- [x] **Step 3: Implement server entrypoint**

Create `backend/src/knowledge_agent/server.py`:

```python
from argparse import ArgumentParser, Namespace
from collections.abc import Sequence

import uvicorn


def parse_args(argv: Sequence[str] | None = None) -> Namespace:
    parser = ArgumentParser(description="Knowledge Agent backend server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    uvicorn.run(
        "knowledge_agent.main:app",
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
```

- [x] **Step 4: Run tests to verify GREEN**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_server.py -q
```

Expected: PASS.

- [x] **Step 5: Commit backend entrypoint**

Run:

```powershell
git add backend/src/knowledge_agent/server.py backend/tests/test_server.py
git commit -m "feat: add packaged backend entrypoint"
```

### Task 2: Tauri Bundled Backend Launch

**Files:**
- Modify: `apps/desktop/src-tauri/src/main.rs`
- Modify: `apps/desktop/src-tauri/src/backend_process.rs`

- [x] **Step 1: Write failing Rust launch tests**

Add tests to `apps/desktop/src-tauri/src/backend_process.rs` proving:

```rust
#[test]
fn resolves_bundled_backend_before_development_fallback() {
    let root = temp_repo();
    let resource_dir = root.join("resources");
    fs::create_dir_all(&resource_dir).unwrap();
    let bundled = resource_dir.join(BUNDLED_BACKEND_EXE);
    fs::write(&bundled, "").unwrap();

    let cwd = root.join("apps/desktop/src-tauri");
    let launch =
        resolve_backend_launch(&cwd, Some(&resource_dir), &HashMap::new()).unwrap();

    assert_eq!(launch.program, bundled);
    assert_eq!(launch.args, vec!["--host", "127.0.0.1", "--port", "8765"]);
    assert_eq!(launch.cwd, resource_dir);

    fs::remove_dir_all(root).unwrap();
}
```

Keep the existing environment override and development fallback tests passing through the new `resolve_backend_launch()` API.

- [x] **Step 2: Run Rust tests to verify RED**

Run from `apps/desktop/src-tauri`:

```powershell
cargo test --locked
```

Expected: FAIL because `resolve_backend_launch` and `BUNDLED_BACKEND_EXE` do not exist.

- [x] **Step 3: Implement bundled backend resolution**

In `backend_process.rs`:

- Add `pub const BUNDLED_BACKEND_EXE: &str = "knowledge-agent-backend-x86_64-pc-windows-msvc.exe";`.
- Add `resolve_backend_launch(current_dir, resource_dir, env)`.
- Preserve `KA_BACKEND_PROGRAM` override.
- Prefer `resource_dir.join(BUNDLED_BACKEND_EXE)` when it exists.
- Fall back to `.venv\Scripts\python.exe -m uvicorn knowledge_agent.main:app`.
- Change `BackendProcess::start()` to `BackendProcess::start(resource_dir: Option<PathBuf>)`.

In `main.rs`, pass:

```rust
let resource_dir = app.path().resource_dir().ok();
app.manage(backend_process::BackendProcess::start(resource_dir));
```

- [x] **Step 4: Run Rust tests to verify GREEN**

Run from `apps/desktop/src-tauri`:

```powershell
cargo test --locked
```

Expected: PASS.

- [x] **Step 5: Commit launcher change**

Run:

```powershell
git add apps/desktop/src-tauri/src/main.rs apps/desktop/src-tauri/src/backend_process.rs
git commit -m "feat: launch bundled backend in release"
```

### Task 3: Release Build Script and Bundle Config

**Files:**
- Create: `scripts/build-release.ps1`
- Modify: `.gitignore`
- Modify: `apps/desktop/src-tauri/tauri.conf.json`
- Create: `apps/desktop/src-tauri/tauri.release.conf.json`
- Modify: `README.md`

- [x] **Step 1: Update `.gitignore`**

Add generated release output paths:

```gitignore
apps/desktop/src-tauri/binaries/
release/
```

- [x] **Step 2: Update Tauri bundle config**

Set Windows installer target to NSIS and configure external binary:

```json
{
  "bundle": {
    "externalBin": ["binaries/knowledge-agent-backend"]
  }
}
```

Keep `apps/desktop/src-tauri/tauri.conf.json` free of `externalBin` so normal `cargo check --locked` does not require generated PyInstaller output. The release script passes `--config src-tauri/tauri.release.conf.json` after the backend executable exists.

- [x] **Step 3: Create release build script**

Create `scripts/build-release.ps1` that:

- Ensures `.venv`.
- Installs `backend[dev]` and `pyinstaller`.
- Builds `knowledge-agent-backend-x86_64-pc-windows-msvc.exe` into `apps/desktop/src-tauri/binaries/`.
- Installs npm dependencies when needed.
- Runs `npm run tauri -- build --bundles nsis`.
- Prints NSIS installer paths and SHA-256 checksums.

- [x] **Step 4: Update README release section**

Document:

- Release prerequisites.
- `.\scripts\build-release.ps1`.
- Installer output under `apps\desktop\src-tauri\target\release\bundle\nsis`.
- Private sharing expectations and unsigned installer warnings.
- Do not commit generated installers, binaries, PDFs, API keys, or local libraries.

- [x] **Step 5: Commit release script/config/docs**

Run:

```powershell
git add .gitignore scripts/build-release.ps1 apps/desktop/src-tauri/tauri.conf.json apps/desktop/src-tauri/tauri.release.conf.json README.md docs/superpowers/plans/2026-06-05-windows-release-packaging-upload-plan.md
git commit -m "build: add windows release packaging"
```

### Task 4: Verification and Installer Build

**Files:**
- No source edits unless verification exposes a bug.

- [ ] **Step 1: Run backend tests**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend tests and build**

Run from `apps/desktop`:

```powershell
npm test
npm run build
```

Expected: PASS.

- [ ] **Step 3: Run Rust verification**

Run from `apps/desktop/src-tauri`:

```powershell
cargo test --locked
cargo check --locked
```

Expected: PASS.

- [ ] **Step 4: Run release build**

Run:

```powershell
.\scripts\build-release.ps1
```

Expected: PASS and at least one `.exe` installer under `apps\desktop\src-tauri\target\release\bundle\nsis`.

- [ ] **Step 5: Smoke bundled backend executable**

If the release build did not already smoke the backend, start:

```powershell
.\apps\desktop\src-tauri\binaries\knowledge-agent-backend-x86_64-pc-windows-msvc.exe --host 127.0.0.1 --port 8765
```

Then call `http://127.0.0.1:8765/health`, expect JSON `{"status":"ok","service":"knowledge-agent-backend"}`, and stop the process.

- [ ] **Step 6: Hygiene checks**

Run:

```powershell
git diff --check
Select-String -Path README.md,docs\**\*,backend\**\*,apps\**\*,scripts\**\* -Pattern 'sk-[A-Za-z0-9]{20,}' -CaseSensitive -ErrorAction SilentlyContinue
git status --short
```

Expected: no whitespace errors, no real API key matches, generated binaries/installers ignored.

### Task 5: Push to GitHub

**Files:**
- Git config only.

- [ ] **Step 1: Configure remote**

Run:

```powershell
git remote add origin https://github.com/coffee181/Thesis-Assistant.git
```

If `origin` already exists, set it to the same URL.

- [ ] **Step 2: Configure proxy for this repository**

Run:

```powershell
git config http.proxy http://127.0.0.1:7897
git config https.proxy http://127.0.0.1:7897
```

- [ ] **Step 3: Verify no generated artifacts are staged**

Run:

```powershell
git status --short
git ls-files | Select-String -Pattern '2301.12652v4.pdf|src-tauri/binaries|target/release/bundle|\.venv|node_modules|KnowledgeAgentLibrary|sk-[A-Za-z0-9]{20,}'
```

Expected: no tracked generated artifacts or secrets.

- [ ] **Step 4: Push**

Run:

```powershell
git push -u origin master
```

Expected: branch uploaded to `coffee181/Thesis-Assistant`. If GitHub authentication fails, report the exact failure and leave the repository ready to push.
