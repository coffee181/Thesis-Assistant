# Windows Release Packaging Design

## Summary

Knowledge Agent needs a Windows release package that installs like ordinary desktop software. The installed app must not depend on the source checkout, `.venv`, Node.js, npm, Rust, or Python being installed by the user.

The release packaging work converts the Python backend into a bundled Windows executable, includes it in the Tauri desktop bundle, and produces a Windows installer with a repeatable PowerShell build command.

## Goals

- Produce a Windows installer that can be launched by a non-developer user.
- Bundle the FastAPI backend as a local executable built by PyInstaller.
- Keep the backend bound to `127.0.0.1:8765`.
- Keep development startup behavior intact: `scripts/dev-desktop.ps1` should continue using the editable backend in `.venv`.
- Prefer an NSIS `.exe` installer for the first release because it matches a familiar Windows setup flow.
- Emit and document the release artifact paths.
- Avoid committing generated binaries, installer output, local libraries, or secrets.

## Non-Goals

- Code signing.
- Auto-update infrastructure.
- Full CI/CD release automation.
- Cross-platform packaging.
- Replacing the current PDF reader or adding new product features.
- Shipping user data, test PDFs, model API keys, or smoke-test libraries.

## Packaging Architecture

The backend packaging layer lives outside the backend runtime code. A PyInstaller entrypoint starts Uvicorn with `knowledge_agent.main:app` on `127.0.0.1:8765`. The build script installs backend dependencies into the local virtual environment, installs PyInstaller if needed, and writes a backend executable under a generated build output directory.

The Tauri bundle includes that backend executable as an external binary. In release mode, the Rust launcher resolves the bundled backend executable from the installed app resources or sidecar location and starts it without requiring `.venv`. In development mode, the launcher keeps the existing repository-based fallback to `.venv\Scripts\python.exe -m uvicorn knowledge_agent.main:app`.

The frontend continues to call `http://127.0.0.1:8765`. The current backend health retry remains the startup readiness mechanism.

## Components

### Backend Release Entrypoint

Create `backend/src/knowledge_agent/server.py` as the PyInstaller entrypoint. It should:

- Start Uvicorn with `knowledge_agent.main:app`.
- Default to host `127.0.0.1` and port `8765`.
- Accept optional `--host` and `--port` arguments for testing and launcher compatibility.

### Release Build Script

Create `scripts/build-release.ps1`. It should:

- Ensure `.venv` exists.
- Install `backend[dev]`.
- Install PyInstaller in `.venv`.
- Remove stale release build output for the backend executable.
- Build the backend executable.
- Install desktop npm dependencies when needed.
- Run the Tauri build for Windows installer targets.
- Print the produced installer path or paths.

The script is a developer/release-engineering tool. It is not installed with the app.

### Tauri Bundle Configuration

Update `apps/desktop/src-tauri/tauri.conf.json` to:

- Use Windows release targets suitable for this project, with `nsis` as the required target.
- Include the backend executable with Tauri v2 `bundle.externalBin`.
- Keep app metadata consistent with the current version `0.1.0`.

The external binary base path is `binaries/knowledge-agent-backend`. The release build script writes the Windows executable to `apps/desktop/src-tauri/binaries/knowledge-agent-backend-x86_64-pc-windows-msvc.exe`, matching Tauri's required target-triple naming convention.

If MSI generation is blocked by missing local WiX tooling, the release is still acceptable when the NSIS installer is produced.

### Rust Backend Launcher

Update `apps/desktop/src-tauri/src/backend_process.rs` so backend launch resolution follows this order:

1. `KA_BACKEND_PROGRAM` and `KA_BACKEND_ARGS` override everything for diagnostics and experiments.
2. A bundled release backend executable is used when present. The resolved executable name is `knowledge-agent-backend-x86_64-pc-windows-msvc.exe` for this Windows release.
3. The development `.venv\Scripts\python.exe -m uvicorn knowledge_agent.main:app` fallback is used when running from the repository checkout.

The launcher should not start a second backend if `127.0.0.1:8765` is already listening. It should continue killing only the child process it owns when the app exits.

## Artifact Expectations

A successful Windows release build must produce at least one ordinary installer:

- Required: NSIS installer `.exe` under `apps/desktop/src-tauri/target/release/bundle/nsis/`.
- Optional: MSI installer `.msi` under `apps/desktop/src-tauri/target/release/bundle/msi/` when tooling is available.

Generated artifacts remain untracked.

## Error Handling

- If PyInstaller is unavailable, `scripts/build-release.ps1` installs it into `.venv`.
- If backend executable creation fails, the release script exits before running Tauri build.
- If Tauri cannot find the backend executable, the build fails rather than producing a broken installer.
- If the release app starts and port `8765` is already occupied, the existing launcher behavior treats the backend as already running.
- If installer generation fails for MSI but NSIS succeeds, the release script can report NSIS success and MSI absence as a non-blocking tooling limitation.

## Testing Strategy

The implementation should use TDD for launcher behavior and any script helper logic that can be tested without producing installers.

Verification commands:

- Backend tests: `.\.venv\Scripts\python -m pytest backend/tests -q`
- Frontend tests: `npm test` from `apps/desktop`
- Frontend build: `npm run build` from `apps/desktop`
- Rust tests/check: `cargo test --locked` and `cargo check --locked` from `apps/desktop/src-tauri`
- Backend executable smoke: run the PyInstaller backend executable, call `/health`, then stop it
- Tauri build: release script or `npm run tauri -- build --bundles nsis`
- Artifact check: verify at least one NSIS installer exists under `apps/desktop/src-tauri/target/release/bundle/nsis/`

## Documentation

Update `README.md` with:

- `scripts/build-release.ps1` usage.
- Release prerequisites.
- Expected installer output path.
- A note that generated installers and backend binaries are not committed.

## Acceptance Criteria

The release packaging work is accepted when:

1. A clean checkout on Windows can run `scripts/build-release.ps1`.
2. The script produces an NSIS installer `.exe`.
3. The installed or release-built app starts a bundled backend without relying on `.venv`.
4. The app health check reaches `ok`.
5. Existing backend, frontend, and Rust tests pass.
6. No generated release binary, installer, local PDF, model key, or local library data is committed.
