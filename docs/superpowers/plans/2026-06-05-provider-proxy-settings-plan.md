# Provider Proxy Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users configure an HTTP proxy for model provider calls from the desktop settings screen.

**Architecture:** Extend existing provider settings with `proxy_url`. Persist it in the SQLite `settings` JSON alongside provider/base URL/model/API key/outbound policy, return it in public settings, and pass it to `httpx.Client(proxy=...)` when the real HTTP provider creates a client. The desktop app adds one `Proxy URL` input and sends it through the existing settings endpoint.

**Tech Stack:** Python 3.13, FastAPI, SQLite, httpx 0.28, pytest, React, TypeScript, Vitest, Testing Library.

---

## Scope

This plan implements:

- `proxy_url` in backend provider settings models, repository persistence, schemas, and public API.
- `HttpChatProvider` support for `httpx.Client(proxy=settings.proxy_url)` when no test client is injected.
- Desktop provider settings type support and one input field for proxy URL.
- Tests proving the proxy value is persisted, hidden API keys remain hidden, and the provider client factory receives the proxy.

This plan does not implement proxy settings for external metadata discovery, open PDF downloads, environment variable proxy import, proxy authentication helpers, or proxy connection testing.

## File Structure

Modify:

```text
backend/
  src/knowledge_agent/
    main.py
    models.py
    providers.py
    repositories.py
    schemas.py
  tests/
    test_api.py
    test_database.py
    test_providers.py
apps/
  desktop/
    src/
      App.test.tsx
      App.tsx
      api.ts
docs/
  superpowers/plans/2026-06-05-provider-proxy-settings-plan.md
```

Responsibilities:

- `models.py`: Add `proxy_url` to private and public provider settings.
- `repositories.py`: Save and load `proxy_url` from JSON while preserving backwards-compatible defaults.
- `schemas.py`: Accept and return `proxy_url`.
- `providers.py`: Create real `httpx.Client` instances with the configured proxy.
- `main.py`: Build `ProviderSettings` from the new request field.
- `App.tsx` and `api.ts`: Add proxy form state and typed request/response fields.
- Tests: Cover persistence, API, provider client construction, and desktop request body.

## Task 1: Backend Provider Proxy Settings

**Files:**
- Modify: `backend/tests/test_database.py`
- Modify: `backend/tests/test_api.py`
- Modify: `backend/tests/test_providers.py`
- Modify: `backend/src/knowledge_agent/models.py`
- Modify: `backend/src/knowledge_agent/repositories.py`
- Modify: `backend/src/knowledge_agent/schemas.py`
- Modify: `backend/src/knowledge_agent/main.py`
- Modify: `backend/src/knowledge_agent/providers.py`

- [ ] **Step 1: Write failing backend tests**

Add backend tests proving:

```python
def test_provider_settings_default_and_roundtrip(tmp_path: Path):
    ...
    saved_settings = settings.save_provider_settings(
        ProviderSettings(
            provider="openai_compatible",
            base_url="https://api.example.test/v1",
            model="research-model",
            api_key="secret",
            outbound_context_policy="snippets_only",
            proxy_url="http://127.0.0.1:7897",
        )
    )
    ...
    assert default_settings.proxy_url is None
    assert saved_settings.proxy_url == "http://127.0.0.1:7897"
    assert reloaded_settings.proxy_url == "http://127.0.0.1:7897"
```

```python
def test_provider_settings_endpoints_hide_api_key(tmp_path: Path):
    ...
    save_response = client.put(
        "/api/settings/provider",
        json={
            "provider": "openai_compatible",
            "base_url": "https://api.example.test/v1",
            "model": "research-model",
            "api_key": "secret-key",
            "outbound_context_policy": "snippets_only",
            "proxy_url": "http://127.0.0.1:7897",
        },
    )
    ...
    assert save_response.json()["proxy_url"] == "http://127.0.0.1:7897"
    assert reload_response.json()["proxy_url"] == "http://127.0.0.1:7897"
```

```python
def test_http_provider_uses_configured_proxy_for_real_clients():
    factory = RecordingHttpClientFactory({"choices": [{"message": {"content": "Proxied answer"}}]})
    provider = HttpChatProvider(http_client_factory=factory)

    answer = provider.complete(
        ProviderSettings(
            provider="openai_compatible",
            base_url="https://api.example.test/v1",
            model="research-model",
            api_key="secret",
            outbound_context_policy="snippets_only",
            proxy_url="http://127.0.0.1:7897",
        ),
        [ProviderMessage(role="user", content="Question")],
    )

    assert answer == "Proxied answer"
    assert factory.calls[0]["proxy"] == "http://127.0.0.1:7897"
```

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py::test_provider_settings_default_and_roundtrip backend/tests/test_api.py::test_provider_settings_endpoints_hide_api_key backend/tests/test_providers.py::test_http_provider_uses_configured_proxy_for_real_clients -q
```

Expected: FAIL because `proxy_url` is not part of the settings models or provider factory.

- [ ] **Step 2: Implement backend support**

Add `proxy_url: str | None = None` to `ProviderSettings` and `PublicProviderSettings`. Persist it in `SettingsRepository`, add it to `ProviderSettingsRequest` and `ProviderSettingsResponse`, and pass it from `save_provider_settings`.

In `HttpChatProvider`, keep injected `http_client` support for existing tests and add an optional factory:

```python
def __init__(self, http_client: object | None = None, timeout: float = 60.0, http_client_factory=httpx.Client) -> None:
    self._http_client = http_client
    self._http_client_factory = http_client_factory
    self._timeout = timeout
```

Create a helper that uses the injected client when present, otherwise opens a real client with `proxy=settings.proxy_url`.

- [ ] **Step 3: Verify backend tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py::test_provider_settings_default_and_roundtrip backend/tests/test_api.py::test_provider_settings_endpoints_hide_api_key backend/tests/test_providers.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit backend slice**

```powershell
git add backend/src/knowledge_agent/models.py backend/src/knowledge_agent/repositories.py backend/src/knowledge_agent/schemas.py backend/src/knowledge_agent/main.py backend/src/knowledge_agent/providers.py backend/tests/test_database.py backend/tests/test_api.py backend/tests/test_providers.py docs/superpowers/plans/2026-06-05-provider-proxy-settings-plan.md
git commit -m "feat: add provider proxy settings"
```

## Task 2: Desktop Provider Proxy Settings

**Files:**
- Modify: `apps/desktop/src/api.ts`
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`

- [ ] **Step 1: Write failing frontend test**

Update `saves provider settings without displaying the raw API key` so default and saved settings include `proxy_url`, type into `Proxy URL`, and assert the request body includes it:

```tsx
await userEvent.type(screen.getByLabelText("Proxy URL"), "http://127.0.0.1:7897");
...
expect(fetchCallBody("/api/settings/provider")).toMatchObject({
  provider: "openai_compatible",
  base_url: "https://api.example.test/v1",
  model: "research-model",
  api_key: "secret-key",
  outbound_context_policy: "snippets_only",
  proxy_url: "http://127.0.0.1:7897",
});
```

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test -- -t "saves provider settings without displaying the raw API key"
```

Expected: FAIL because the `Proxy URL` field does not exist.

- [ ] **Step 2: Implement desktop support**

Add `proxy_url: string | null` to `ProviderSettings` and `SaveProviderSettingsRequest` in `api.ts`. Add `proxyUrl` state in `App.tsx`, hydrate it from `providerSettings.proxy_url`, include it in `saveProviderSettings`, and add this input near Base URL:

```tsx
<label htmlFor="proxy-url">Proxy URL</label>
<input
  id="proxy-url"
  value={proxyUrl}
  onChange={(event) => setProxyUrl(event.target.value)}
  placeholder="http://127.0.0.1:7897"
/>
```

- [ ] **Step 3: Verify frontend tests pass**

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
```

Expected: PASS.

- [ ] **Step 4: Final verification and commit**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm run build
```

Expected: all commands exit 0.

Commit:

```powershell
git add apps/desktop/src/api.ts apps/desktop/src/App.test.tsx apps/desktop/src/App.tsx
git commit -m "feat: expose provider proxy settings"
```

## Self-Review Notes

- Spec coverage: Implements the explicit model-provider proxy setting in the design's provider/privacy and error-handling sections.
- Placeholder scan: No TBD/TODO/fill-in-later text remains.
- Type consistency: `proxy_url` is used consistently across backend JSON, Python dataclasses, TypeScript types, and request bodies.
