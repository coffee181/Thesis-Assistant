from knowledge_agent.models import ProviderSettings
from knowledge_agent.providers import HttpChatProvider, ProviderMessage


class RecordingHttpClient:
    def __init__(self, response_payload: dict):
        self.response_payload = response_payload
        self.requests: list[dict[str, object]] = []

    def post(
        self,
        url: str,
        json: dict,
        headers: dict | None = None,
        timeout: float | None = None,
    ):
        self.requests.append(
            {
                "url": url,
                "json": json,
                "headers": headers or {},
                "timeout": timeout,
            }
        )
        return RecordingResponse(self.response_payload)


class RecordingResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_openai_compatible_provider_routes_chat_completion():
    http_client = RecordingHttpClient(
        {"choices": [{"message": {"content": "Grounded answer"}}]}
    )
    provider = HttpChatProvider(http_client=http_client)

    answer = provider.complete(
        ProviderSettings(
            provider="openai_compatible",
            base_url="https://api.example.test/v1",
            model="research-model",
            api_key="secret",
            outbound_context_policy="snippets_only",
        ),
        [ProviderMessage(role="user", content="Question")],
    )

    assert answer == "Grounded answer"
    assert http_client.requests[0]["url"] == "https://api.example.test/v1/chat/completions"
    assert http_client.requests[0]["headers"]["Authorization"] == "Bearer secret"
    assert http_client.requests[0]["json"] == {
        "model": "research-model",
        "messages": [{"role": "user", "content": "Question"}],
        "temperature": 0.2,
    }


def test_ollama_provider_routes_local_chat():
    http_client = RecordingHttpClient({"message": {"content": "Local answer"}})
    provider = HttpChatProvider(http_client=http_client)

    answer = provider.complete(
        ProviderSettings(
            provider="ollama",
            base_url="http://127.0.0.1:11434",
            model="llama3.1",
            api_key=None,
            outbound_context_policy="snippets_only",
        ),
        [ProviderMessage(role="user", content="Question")],
    )

    assert answer == "Local answer"
    assert http_client.requests[0]["url"] == "http://127.0.0.1:11434/api/chat"
    assert "Authorization" not in http_client.requests[0]["headers"]
    assert http_client.requests[0]["json"] == {
        "model": "llama3.1",
        "messages": [{"role": "user", "content": "Question"}],
        "stream": False,
    }
