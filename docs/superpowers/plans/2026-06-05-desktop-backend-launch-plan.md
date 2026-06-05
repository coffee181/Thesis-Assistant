# Desktop Backend Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Windows-first Tauri desktop shell start and own the local Python backend during desktop runs.

**Architecture:** Add a small Rust launcher module in the Tauri app that resolves the repository backend command in development, supports explicit environment overrides for packaged sidecars, avoids starting a duplicate backend when port 8765 is already listening, and kills the owned child process on app shutdown. Add frontend startup retry so the React app waits briefly for the backend that Tauri just spawned instead of marking the app offline after one failed fetch.

**Tech Stack:** Tauri 2, Rust `std::process`, Rust unit tests, React/Vitest, existing PowerShell dev scripts.

---

### Task 1: Rust Backend Launch Resolution

**Files:**
- Create: `apps/desktop/src-tauri/src/backend_process.rs`
- Modify: `apps/desktop/src-tauri/src/main.rs`

- [ ] **Step 1: Write failing Rust tests**

Create `apps/desktop/src-tauri/src/backend_process.rs` with only the public API and these tests first:

```rust
use std::collections::HashMap;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BackendLaunch {
    pub program: PathBuf,
    pub args: Vec<String>,
    pub cwd: PathBuf,
}

pub fn resolve_backend_launch_from_env(
    _current_dir: &Path,
    _env: &HashMap<String, String>,
) -> Option<BackendLaunch> {
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_repo() -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!("ka-launch-test-{nonce}"));
        fs::create_dir_all(root.join("backend")).unwrap();
        fs::create_dir_all(root.join("apps/desktop/src-tauri")).unwrap();
        fs::write(root.join("backend/pyproject.toml"), "").unwrap();
        fs::write(root.join("apps/desktop/package.json"), "{}").unwrap();
        root
    }

    #[test]
    fn resolves_development_backend_from_repo_root() {
        let root = temp_repo();
        let cwd = root.join("apps/desktop/src-tauri");
        let launch = resolve_backend_launch_from_env(&cwd, &HashMap::new()).unwrap();

        assert_eq!(launch.cwd, root);
        assert!(launch.program.ends_with(".venv\\Scripts\\python.exe"));
        assert_eq!(
            launch.args,
            vec![
                "-m",
                "uvicorn",
                "knowledge_agent.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8765"
            ]
        );

        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn explicit_backend_program_and_args_override_development_resolution() {
        let mut env = HashMap::new();
        env.insert("KA_BACKEND_PROGRAM".to_string(), "F:\\bundle\\backend.exe".to_string());
        env.insert(
            "KA_BACKEND_ARGS".to_string(),
            "--host 127.0.0.1 --port 8765".to_string(),
        );

        let launch = resolve_backend_launch_from_env(Path::new("F:\\nowhere"), &env).unwrap();

        assert_eq!(launch.program, PathBuf::from("F:\\bundle\\backend.exe"));
        assert_eq!(launch.args, vec!["--host", "127.0.0.1", "--port", "8765"]);
        assert_eq!(launch.cwd, PathBuf::from("F:\\nowhere"));
    }
}
```

Modify `apps/desktop/src-tauri/src/main.rs` to declare the module:

```rust
mod backend_process;

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("failed to run Knowledge Agent");
}
```

- [ ] **Step 2: Run Rust tests to verify RED**

Run:

```powershell
cd apps\desktop\src-tauri
cargo test --locked backend_process::tests -- --nocapture
```

Expected: FAIL because launch resolution returns `None`.

- [ ] **Step 3: Implement launch resolution**

Replace the stub with helpers that:
- Read `KA_BACKEND_PROGRAM` and optional whitespace-split `KA_BACKEND_ARGS`.
- Walk upward from `current_dir` until a directory containing `backend/pyproject.toml` and `apps/desktop/package.json` is found.
- Return `.venv\Scripts\python.exe -m uvicorn knowledge_agent.main:app --host 127.0.0.1 --port 8765` with `cwd` set to the repo root.

- [ ] **Step 4: Run Rust tests to verify GREEN**

Run:

```powershell
cd apps\desktop\src-tauri
cargo test --locked backend_process::tests -- --nocapture
```

Expected: PASS.

### Task 2: Tauri Process Ownership

**Files:**
- Modify: `apps/desktop/src-tauri/src/backend_process.rs`
- Modify: `apps/desktop/src-tauri/src/main.rs`

- [ ] **Step 1: Write failing tests for port detection**

Add pure tests in `backend_process.rs`:

```rust
#[test]
fn reports_unused_backend_port_as_not_running() {
    assert!(!is_backend_port_open("127.0.0.1:9"));
}
```

- [ ] **Step 2: Run test to verify RED**

Run:

```powershell
cd apps\desktop\src-tauri
cargo test --locked backend_process::tests::reports_unused_backend_port_as_not_running -- --nocapture
```

Expected: FAIL because `is_backend_port_open` does not exist.

- [ ] **Step 3: Implement process owner**

Add:
- `pub const BACKEND_ADDR: &str = "127.0.0.1:8765";`
- `pub fn is_backend_port_open(addr: &str) -> bool`
- `pub struct BackendProcess { child: Option<std::process::Child> }`
- `impl BackendProcess { pub fn start() -> Self }`
- `Drop` that kills and waits for the child when owned.

`start()` must return a no-child owner if the port is already listening or no launch command can be resolved.

Update `main.rs`:

```rust
mod backend_process;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            app.manage(backend_process::BackendProcess::start());
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("failed to run Knowledge Agent");
}
```

- [ ] **Step 4: Run Rust tests to verify GREEN**

Run:

```powershell
cd apps\desktop\src-tauri
cargo test --locked backend_process::tests -- --nocapture
```

Expected: PASS.

### Task 3: Frontend Startup Retry

**Files:**
- Modify: `apps/desktop/src/api.ts`
- Modify: `apps/desktop/src/App.test.tsx`

- [ ] **Step 1: Write failing frontend test**

Add an App test:

```typescript
it("waits for a backend that is still starting", async () => {
  fetchMock
    .mockRejectedValueOnce(new Error("connection refused"))
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "ok", service: "knowledge-agent-backend" }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => defaultLibraryStatus,
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ papers: [] }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => defaultProviderSettings,
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => emptyJobsResponse,
    });

  render(<App />);

  expect(await screen.findByText("Backend: ok")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(6);
});
```

- [ ] **Step 2: Run frontend test to verify RED**

Run:

```powershell
cd apps\desktop
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test -- --run -t "waits for a backend that is still starting"
```

Expected: FAIL because startup currently makes a single health request.

- [ ] **Step 3: Implement health retry**

In `apps/desktop/src/api.ts`, add:

```typescript
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export async function getHealthWithRetry(
  attempts = 20,
  intervalMs = 250,
): Promise<HealthResponse> {
  let lastError: unknown = null;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      return await getHealth();
    } catch (error) {
      lastError = error;
      if (attempt < attempts - 1) await delay(intervalMs);
    }
  }
  throw lastError instanceof Error ? lastError : new Error("Backend health check failed");
}
```

Update `App.tsx` to import and call `getHealthWithRetry()` during initial load.

- [ ] **Step 4: Run frontend test to verify GREEN**

Run:

```powershell
cd apps\desktop
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test -- --run -t "waits for a backend that is still starting"
```

Expected: PASS.

### Task 4: Docs and Verification

**Files:**
- Modify: `README.md`
- Modify: `scripts/dev-desktop.ps1`

- [ ] **Step 1: Update Windows dev script**

In `scripts/dev-desktop.ps1`, before running Tauri, ensure the backend venv exists and install the editable backend:

```powershell
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  python -m venv .venv
}

.\.venv\Scripts\python -m pip install -e "backend[dev]"
```

- [ ] **Step 2: Update README**

Document:
- `scripts\dev-desktop.ps1` now starts the desktop shell and Tauri will start the local backend.
- `KA_BACKEND_PROGRAM` and `KA_BACKEND_ARGS` can override the backend command for sidecar experiments.

- [ ] **Step 3: Run full verification**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
cd apps\desktop
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm run build
cd apps\desktop\src-tauri
cargo test --locked
cargo check --locked
cd F:\knowledge-agent
git diff --check
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```powershell
git add README.md scripts/dev-desktop.ps1 apps/desktop/src/api.ts apps/desktop/src/App.tsx apps/desktop/src/App.test.tsx apps/desktop/src-tauri/src/main.rs apps/desktop/src-tauri/src/backend_process.rs docs/superpowers/plans/2026-06-05-desktop-backend-launch-plan.md
git commit -m "feat: launch backend from desktop shell"
```
