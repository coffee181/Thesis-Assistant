# Provider Settings and Traceable Q&A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the app configure OpenAI-compatible or Ollama chat providers and ask current-paper questions with page/snippet citations.

**Architecture:** Store provider settings and Q&A history in SQLite. Add a small provider boundary that can route to OpenAI-compatible `/chat/completions` or Ollama `/api/chat`, while the assistant service assembles only current-paper snippets and returns citations independent of the model text. Extend the desktop assistant panel with provider settings, a question box, answer display, and cited snippets.

**Tech Stack:** Python 3.13, FastAPI, SQLite, httpx, pytest, React, TypeScript, Vitest, Testing Library.

---

## Scope

This plan implements:

- Local provider settings storage for `none`, `openai_compatible`, and `ollama`.
- API-safe settings responses that never echo the API key.
- Provider routing for OpenAI-compatible and Ollama chat APIs.
- Current-paper strict traceable Q&A using extracted chunks.
- Local Q&A history records with cited chunk references.
- Desktop settings form and ask workflow.

This plan does not implement streaming responses, selected-text translation, cross-library synthesis, semantic/vector retrieval, note saving, or encrypted credential storage.

## File Structure

Create or modify:

```text
backend/
  pyproject.toml
  src/knowledge_agent/
    assistant.py
    db.py
    main.py
    models.py
    providers.py
    repositories.py
    schemas.py
  tests/
    test_api.py
    test_assistant.py
    test_database.py
    test_providers.py
apps/
  desktop/
    src/
      App.test.tsx
      App.tsx
      api.ts
      styles.css
docs/
  superpowers/plans/2026-06-05-provider-traceable-qna-plan.md
```

Responsibilities:

- `backend/src/knowledge_agent/db.py`: Add `settings` and `qna_entries` tables.
- `backend/src/knowledge_agent/repositories.py`: Add provider settings persistence, qna persistence, and current-paper chunk relevance helpers.
- `backend/src/knowledge_agent/providers.py`: Convert stored settings to provider-specific HTTP chat calls.
- `backend/src/knowledge_agent/assistant.py`: Assemble current-paper context, enforce configured provider/privacy policy, call the provider, and return citations.
- `backend/src/knowledge_agent/main.py`: Add settings and ask endpoints.
- `apps/desktop/src/api.ts`: Add settings and ask client calls.
- `apps/desktop/src/App.tsx`: Add provider settings form and current-paper question UI.

## Task 1: Settings and Q&A Persistence

**Files:**
- Modify: `backend/src/knowledge_agent/db.py`
- Modify: `backend/src/knowledge_agent/models.py`
- Modify: `backend/src/knowledge_agent/repositories.py`
- Modify: `backend/tests/test_database.py`

- [ ] **Step 1: Write failing persistence tests**

Add tests proving:

- `init_db` creates `settings` and `qna_entries`.
- default provider settings are `provider="none"`, `outbound_context_policy="snippets_only"`, and `api_key_configured=False`.
- saving provider settings persists provider/base URL/model/policy and never exposes the raw API key through the public value object.
- creating a Q&A entry stores question, answer, mode, provider, and cited chunks.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py -q
```

Expected: FAIL because settings and qna repositories do not exist.

- [ ] **Step 2: Implement persistence**

Add:

- `settings(key text primary key, value text not null, updated_at text not null default current_timestamp)`.
- `qna_entries(id integer primary key autoincrement, paper_id integer not null references papers(id) on delete cascade, question text not null, answer text not null, cited_chunks text not null, mode text not null, provider text not null, created_at text not null default current_timestamp)`.
- `ProviderSettings`, `PublicProviderSettings`, and `QnaEntry` dataclasses.
- `SettingsRepository.get_provider_settings`, `SettingsRepository.save_provider_settings`.
- `QnaRepository.create`, `QnaRepository.list_for_paper`.
- `ChunksRepository.relevant_for_paper`, using simple token-overlap scoring over current-paper chunks and falling back to the earliest chunks.

- [ ] **Step 3: Verify tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_database.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add backend/src/knowledge_agent/db.py backend/src/knowledge_agent/models.py backend/src/knowledge_agent/repositories.py backend/tests/test_database.py
git commit -m "feat: store provider settings and qna history"
```

## Task 2: Provider Routing and Assistant Context Assembly

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/src/knowledge_agent/providers.py`
- Create: `backend/src/knowledge_agent/assistant.py`
- Create: `backend/tests/test_providers.py`
- Create: `backend/tests/test_assistant.py`

- [ ] **Step 1: Write failing provider and assistant tests**

Add tests proving:

- OpenAI-compatible routing posts to `<base_url>/chat/completions`, uses bearer auth when an API key exists, and parses `choices[0].message.content`.
- Ollama routing posts to `<base_url>/api/chat`, sends `stream=false`, and parses `message.content`.
- Assistant prompts include only selected current-paper snippets, include page labels, and do not include unrelated paper chunks.
- Assistant returns citations with paper title, page number, original snippet, and source span.
- If provider is `none`, asking with available evidence raises a provider configuration error.
- If no extracted chunks exist, assistant returns an insufficient-evidence answer without calling the provider.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_providers.py backend/tests/test_assistant.py -q
```

Expected: FAIL because provider and assistant modules do not exist.

- [ ] **Step 2: Add runtime HTTP dependency**

Move `httpx>=0.27.0` from dev dependencies into production dependencies because provider calls use it at runtime.

Install:

```powershell
.\.venv\Scripts\python -m pip install -e "backend[dev]"
```

- [ ] **Step 3: Implement provider routing**

Implement:

- `ProviderCallError`.
- `ProviderMessage(role: str, content: str)`.
- `HttpChatProvider.complete(settings: ProviderSettings, messages: list[ProviderMessage]) -> str`.
- OpenAI-compatible payload: `{"model": settings.model, "messages": [...], "temperature": 0.2}`.
- Ollama payload: `{"model": settings.model, "messages": [...], "stream": False}`.

- [ ] **Step 4: Implement assistant service**

Implement:

- `AssistantConfig(max_context_chunks=4)`.
- `TraceableAnswer(answer, citations, mode, provider)`.
- `answer_current_paper_question(conn, paper_id, question, chat_provider, config=AssistantConfig())`.
- Strict context prompt in Chinese that tells the model to use only supplied snippets and say evidence is insufficient when needed.
- Save the Q&A result through `QnaRepository`.

- [ ] **Step 5: Verify provider and assistant tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_providers.py backend/tests/test_assistant.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/pyproject.toml backend/src/knowledge_agent/providers.py backend/src/knowledge_agent/assistant.py backend/tests/test_providers.py backend/tests/test_assistant.py
git commit -m "feat: add provider routed traceable assistant"
```

## Task 3: Settings and Ask APIs

**Files:**
- Modify: `backend/src/knowledge_agent/schemas.py`
- Modify: `backend/src/knowledge_agent/main.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Add tests proving:

- `GET /api/settings/provider` returns default public settings.
- `PUT /api/settings/provider` saves settings and responds with `api_key_configured=True` without returning the raw key.
- `POST /api/papers/{paper_id}/assistant/ask` calls an injected fake provider with current-paper snippets and returns answer citations.
- Asking without provider settings returns 400.
- Missing paper returns 404.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py -q
```

Expected: FAIL because endpoints are missing.

- [ ] **Step 2: Implement schemas and endpoints**

Add request/response schemas:

- `ProviderSettingsRequest`
- `ProviderSettingsResponse`
- `AskPaperQuestionRequest`
- `CitationResponse`
- `AskPaperQuestionResponse`

Update `create_app(library_dir: Path | None = None, chat_provider: ChatProvider | None = None)` so tests can inject a fake provider.

- [ ] **Step 3: Verify API tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add backend/src/knowledge_agent/schemas.py backend/src/knowledge_agent/main.py backend/tests/test_api.py
git commit -m "feat: expose provider settings and traceable ask api"
```

## Task 4: Desktop Provider Settings and Ask Workflow

**Files:**
- Modify: `apps/desktop/src/api.ts`
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/styles.css`

- [ ] **Step 1: Write failing frontend tests**

Add tests proving:

- The assistant panel loads provider settings and saves an OpenAI-compatible provider without exposing the raw key.
- With a paper open, entering a question sends `POST /api/papers/{paper_id}/assistant/ask`.
- The answer and cited page/snippet are displayed in the assistant panel.

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
```

Expected: FAIL because the UI and API client methods are missing.

- [ ] **Step 2: Implement API client calls**

Add:

- `getProviderSettings()`
- `saveProviderSettings(settings)`
- `askPaperQuestion(paperId, question)`
- response types for provider settings, answers, and citations.

- [ ] **Step 3: Implement UI**

Extend the assistant panel with:

- Provider selector.
- Base URL input.
- Model input.
- API key input.
- Outbound context policy selector.
- Save settings button.
- Question textarea.
- Ask button disabled until a paper is open and question is not blank.
- Answer display with citations showing `Page N` and the original snippet.

- [ ] **Step 4: Verify frontend tests pass**

Run:

```powershell
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add apps/desktop/src/api.ts apps/desktop/src/App.test.tsx apps/desktop/src/App.tsx apps/desktop/src/styles.css
git commit -m "feat: add desktop traceable assistant workflow"
```

## Final Verification

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm test
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'; npm run build
```

Expected: all commands exit 0.

