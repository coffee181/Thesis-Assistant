# Assistant SSE Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a streaming assistant path so current-paper Q&A exposes observable progress while keeping existing traceable final answers.

**Architecture:** Keep the existing synchronous `/api/papers/{paper_id}/assistant/ask` endpoint as the stable API. Add `/api/papers/{paper_id}/assistant/ask/stream` using Server-Sent Events; it emits `started`, `context`, `final`, and `error` events. The frontend uses `fetch()` plus `ReadableStream` parsing so Tauri/desktop runs do not need an `EventSource` POST workaround.

**Tech Stack:** Python 3.13, FastAPI `StreamingResponse`, React, TypeScript, Vitest, pytest.

---

## Scope

This plan implements:

- Backend SSE event formatting.
- A current-paper assistant streaming endpoint with progress/final/error events.
- Frontend streaming API parsing.
- Assistant panel progress text during streaming asks.
- Tests proving backend event sequence and frontend streaming behavior.

This plan does not implement provider token streaming, WebSockets, streaming selected-text translation, cancellation, or background job conversion for downloads.

## File Structure

Create:

```text
backend/src/knowledge_agent/streaming.py
backend/tests/test_streaming.py
```

Modify:

```text
backend/src/knowledge_agent/main.py
backend/tests/test_api.py
apps/desktop/src/api.ts
apps/desktop/src/App.tsx
apps/desktop/src/App.test.tsx
README.md
docs/superpowers/plans/2026-06-05-assistant-sse-streaming-plan.md
```

Responsibilities:

- `streaming.py`: Encode named SSE events as `event: <name>\ndata: <json>\n\n`.
- `main.py`: Add streaming assistant endpoint and map known errors to SSE `error` events.
- `api.ts`: Add `askPaperQuestionStream()` and a small SSE parser for fetch streams.
- `App.tsx`: Prefer streaming ask; update progress state from events; set final answer on `final`.
- Tests: Cover backend stream events and frontend stream parsing/progress.

## Task 1: Backend SSE Endpoint

**Files:**

- Create: `backend/src/knowledge_agent/streaming.py`
- Create: `backend/tests/test_streaming.py`
- Modify: `backend/src/knowledge_agent/main.py`
- Modify: `backend/tests/test_api.py`

- [x] **Step 1: Write failing SSE formatter test**

Create `backend/tests/test_streaming.py`:

```python
from knowledge_agent.streaming import sse_event


def test_sse_event_encodes_json_payload():
    assert sse_event("context", {"chunk_count": 2}) == (
        'event: context\n'
        'data: {"chunk_count":2}\n\n'
    )
```

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_streaming.py -q
```

Expected: FAIL because `knowledge_agent.streaming` does not exist.

- [x] **Step 2: Implement SSE formatter**

Add `sse_event(name: str, payload: dict[str, object]) -> str` using `json.dumps(..., ensure_ascii=False, separators=(",", ":"))`.

- [x] **Step 3: Write failing backend stream endpoint tests**

Add tests to `backend/tests/test_api.py`:

- `test_ask_current_paper_stream_returns_started_context_and_final_events`
- `test_ask_current_paper_stream_returns_error_event_for_provider_failure`

Use `TestClient.stream("POST", f"/api/papers/{paper_id}/assistant/ask/stream", json={"question": "..."})`, then assert:

```python
body = "".join(response.iter_text())
assert "event: started" in body
assert '"paper_id":' in body
assert "event: context" in body
assert '"citation_count":1' in body
assert "event: final" in body
assert "retrieval augmented generation" in body
```

For provider failure, use `ApiFailingChatProvider`, assert `event: error` and provider error detail.

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_api.py::test_ask_current_paper_stream_returns_started_context_and_final_events backend/tests/test_api.py::test_ask_current_paper_stream_returns_error_event_for_provider_failure -q
```

Expected: FAIL because endpoint is missing.

- [x] **Step 4: Implement backend endpoint**

Add imports:

```python
from fastapi.responses import FileResponse, StreamingResponse
from knowledge_agent.streaming import sse_event
```

Add endpoint after the synchronous ask endpoint:

```python
@app.post("/api/papers/{paper_id}/assistant/ask/stream")
def ask_current_paper_stream(paper_id: int, request: AskPaperQuestionRequest) -> StreamingResponse:
    def events():
        yield sse_event("started", {"paper_id": paper_id})
        try:
            with connect(config.database_path) as conn:
                answer = answer_current_paper_question(...)
            yield sse_event("context", {"citation_count": len(answer.citations)})
            yield sse_event("final", {...same response shape...})
        except KeyError:
            yield sse_event("error", {"status": 404, "detail": "paper not found"})
        except ProviderConfigurationError as exc:
            yield sse_event("error", {"status": 400, "detail": str(exc)})
        except ProviderCallError as exc:
            yield sse_event("error", {"status": 502, "detail": str(exc)})
    return StreamingResponse(events(), media_type="text/event-stream")
```

- [x] **Step 5: Verify backend tests pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests/test_streaming.py backend/tests/test_api.py -q
```

Expected: PASS.

## Task 2: Frontend Streaming Ask Flow

**Files:**

- Modify: `apps/desktop/src/api.ts`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `README.md`

- [x] **Step 1: Write failing frontend test**

Add a test near the current-paper ask test:

```tsx
it("streams current-paper ask progress before displaying the final answer", async () => {
  // Queue initial reader load and a fetch Response with a ReadableStream body:
  // event: started
  // event: context
  // event: final
  // Assert the request goes to /assistant/ask/stream.
  // Assert progress text appears.
  // Assert final answer and citation appear.
});
```

Run:

```powershell
cd apps\desktop
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'
npm test -- src/App.test.tsx -t "streams current-paper ask progress"
```

Expected: FAIL because frontend still calls `/assistant/ask`.

- [x] **Step 2: Implement frontend stream parser and API**

In `api.ts`, add:

```ts
export type AssistantStreamEvent =
  | { event: "started"; data: { paper_id: number } }
  | { event: "context"; data: { citation_count: number } }
  | { event: "final"; data: AskPaperQuestionResponse }
  | { event: "error"; data: { status: number; detail: string } };

export async function askPaperQuestionStream(
  paperId: number,
  question: string,
  onEvent: (event: AssistantStreamEvent) => void,
): Promise<AskPaperQuestionResponse> { ... }
```

Parse `text/event-stream` chunks by splitting on blank lines. Throw on `error`; return the final response.

- [x] **Step 3: Update `App.tsx` ask flow**

Import `askPaperQuestionStream`, add `assistantProgress` state, and change `handleAsk` to:

- Clear previous answer and set `"Starting assistant..."`.
- Call `askPaperQuestionStream`.
- Set progress to `"Gathering cited context..."` on `context`.
- Set final answer on `final`.
- Clear progress after completion.
- On stream failure, fall back to existing `askPaperQuestion()` once.

- [x] **Step 4: Update README current slice**

Add:

```markdown
- Streaming assistant Q&A endpoint and desktop progress updates for current-paper questions.
```

- [x] **Step 5: Verify frontend tests and build pass**

Run:

```powershell
cd apps\desktop
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'
npm test
npm run build
```

Expected: PASS.

## Final Verification

Run:

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
cd apps\desktop
$env:npm_config_cache='F:\knowledge-agent\apps\desktop\.npm-cache'
npm test
npm run build
git diff --check
```

Expected: all commands exit 0, with only line-ending warnings if Git emits them on Windows.

## Commit

```powershell
git add backend/src/knowledge_agent/streaming.py backend/src/knowledge_agent/main.py backend/tests/test_streaming.py backend/tests/test_api.py apps/desktop/src/api.ts apps/desktop/src/App.tsx apps/desktop/src/App.test.tsx README.md docs/superpowers/plans/2026-06-05-assistant-sse-streaming-plan.md
git commit -m "feat: stream current paper assistant answers"
```

## Self-Review Notes

- Spec coverage: Adds streaming support for assistant interaction while preserving strict traceable final answers.
- Placeholder scan: No TBD/TODO placeholders remain.
- Type consistency: The final SSE payload reuses `AskPaperQuestionResponse`.
