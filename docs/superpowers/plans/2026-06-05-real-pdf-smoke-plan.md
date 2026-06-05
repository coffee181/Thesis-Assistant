# Real PDF Smoke Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repeatable Windows-friendly smoke test for importing a real local PDF and asking a current-paper question through the configured OpenAI-compatible provider.

**Architecture:** Keep production data and secrets out of the repository. Add a small backend script that creates a temporary managed library, imports a local PDF, verifies extracted reader context, configures a provider from environment variables, asks the current-paper assistant, and checks citations. Harden OpenAI-compatible URL handling so a root gateway URL such as `https://example.test/` resolves to `/v1/chat/completions` while existing `/v1` settings still work.

**Tech Stack:** Python 3.13, FastAPI `TestClient`, pytest, existing backend provider and assistant modules.

---

### Task 1: OpenAI-Compatible Root URL Handling

**Files:**
- Modify: `backend/src/knowledge_agent/providers.py`
- Test: `backend/tests/test_providers.py`

- [ ] **Step 1: Write the failing provider URL test**

Add this test to `backend/tests/test_providers.py`:

```python
def test_openai_compatible_provider_accepts_gateway_root_url():
    http_client = RecordingHttpClient(
        {"choices": [{"message": {"content": "Root answer"}}]}
    )
    provider = HttpChatProvider(http_client=http_client)

    answer = provider.complete(
        ProviderSettings(
            provider="openai_compatible",
            base_url="https://api.example.test/",
            model="research-model",
            api_key="secret",
            outbound_context_policy="snippets_only",
        ),
        [ProviderMessage(role="user", content="Question")],
    )

    assert answer == "Root answer"
    assert http_client.requests[0]["url"] == "https://api.example.test/v1/chat/completions"
```

- [ ] **Step 2: Run provider test to verify RED**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_providers.py::test_openai_compatible_provider_accepts_gateway_root_url -q
```

Expected: FAIL because the provider currently posts to `https://api.example.test/chat/completions`.

- [ ] **Step 3: Implement URL normalization**

In `backend/src/knowledge_agent/providers.py`, add a helper that preserves existing `/v1` paths and appends `/v1` when the configured root has no API path:

```python
def _openai_chat_completions_url(settings: ProviderSettings) -> str:
    base_url = _required_base_url(settings).rstrip("/")
    if base_url.endswith("/chat/completions"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url}/v1/chat/completions"
```

Use this helper inside `_complete_openai_compatible()`.

- [ ] **Step 4: Run provider tests to verify GREEN**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_providers.py -q
```

Expected: PASS.

### Task 2: Real PDF Smoke Script

**Files:**
- Create: `scripts/smoke_real_pdf.py`
- Test: `backend/tests/test_smoke_real_pdf.py`

- [ ] **Step 1: Write failing smoke script tests**

Create `backend/tests/test_smoke_real_pdf.py` with tests that prove:
- `build_settings_from_env()` reads provider settings from environment variables.
- `run_smoke()` imports a PDF, loads reader context, saves provider settings, asks a current-paper question, and returns a summary with citations.
- Missing PDF path returns exit code `2` through `main()`.

Use an in-process fake chat provider for the test so no network calls happen.

- [ ] **Step 2: Run smoke script tests to verify RED**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_smoke_real_pdf.py -q
```

Expected: FAIL because `scripts/smoke_real_pdf.py` does not exist.

- [ ] **Step 3: Implement smoke script**

Create `scripts/smoke_real_pdf.py` with:
- `SmokeConfig`
- `SmokeResult`
- `build_settings_from_env(env)`
- `run_smoke(config, chat_provider=None)`
- `main(argv=None)`

Environment variables:
- `KA_SMOKE_PDF`: local PDF path.
- `KA_SMOKE_BASE_URL`: OpenAI-compatible base URL.
- `KA_SMOKE_API_KEY`: provider API key.
- `KA_SMOKE_MODEL`: model name.
- `KA_SMOKE_PROXY_URL`: optional proxy, for example `http://127.0.0.1:7897`.
- `KA_SMOKE_LIBRARY_DIR`: optional persistent library dir; omit to use a temporary directory.
- `KA_SMOKE_QUESTION`: optional Chinese question, defaulting to a current-paper summary question.

The script prints a concise JSON summary and exits:
- `0` on success.
- `2` for missing required local inputs/settings.
- `1` for import, extraction, or provider failures.

- [ ] **Step 4: Run smoke script tests to verify GREEN**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_smoke_real_pdf.py -q
```

Expected: PASS.

### Task 3: Documentation and Real Local Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document the smoke test command**

Add a README section showing PowerShell environment variables without real secrets:

```powershell
$env:KA_SMOKE_PDF='F:\knowledge-agent\2301.12652v4.pdf'
$env:KA_SMOKE_BASE_URL='https://keungliang.dpdns.org/'
$env:KA_SMOKE_MODEL='glm-5.1'
$env:KA_SMOKE_API_KEY='<your key>'
$env:KA_SMOKE_PROXY_URL='http://127.0.0.1:7897'
.\.venv\Scripts\python .\scripts\smoke_real_pdf.py
```

- [ ] **Step 2: Run targeted and full verification**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_providers.py backend/tests/test_smoke_real_pdf.py -q
.\.venv\Scripts\python -m pytest backend/tests -q
cd apps\desktop
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm run build
cd apps\desktop\src-tauri
cargo check --locked
git diff --check
```

Expected: PASS.

- [ ] **Step 3: Optionally run the real local PDF smoke test**

Run only when the real PDF and provider credentials are available in the shell environment:

```powershell
$env:KA_SMOKE_PDF='F:\knowledge-agent\2301.12652v4.pdf'
$env:KA_SMOKE_BASE_URL='https://keungliang.dpdns.org/'
$env:KA_SMOKE_MODEL='glm-5.1'
$env:KA_SMOKE_API_KEY='<your key>'
$env:KA_SMOKE_PROXY_URL='http://127.0.0.1:7897'
.\.venv\Scripts\python .\scripts\smoke_real_pdf.py
```

Expected: exit 0 and JSON containing `paper_title`, positive `page_count`, positive `citation_count`, and a non-empty `answer_preview`.

- [ ] **Step 4: Commit**

Run:

```powershell
git add docs/superpowers/plans/2026-06-05-real-pdf-smoke-plan.md backend/src/knowledge_agent/providers.py backend/tests/test_providers.py backend/tests/test_smoke_real_pdf.py scripts/smoke_real_pdf.py README.md
git commit -m "test: add real pdf assistant smoke test"
```
