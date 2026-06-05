import pytest

from knowledge_agent.models import ProviderSettings
from knowledge_agent.providers import HttpChatProvider, ProviderCallError, ProviderMessage


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


class NonJsonResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        raise ValueError("not JSON")


class NonJsonHttpClient:
    def post(
        self,
        url: str,
        json: dict,
        headers: dict | None = None,
        timeout: float | None = None,
    ):
        return NonJsonResponse()


class RecordingHttpClientFactory:
    def __init__(self, response_payload: dict):
        self.response_payload = response_payload
        self.calls: list[dict[str, object]] = []
        self.clients: list[RecordingHttpClient] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        client = RecordingContextHttpClient(self.response_payload)
        self.clients.append(client)
        return client


class RecordingContextHttpClient(RecordingHttpClient):
    def __init__(self, response_payload: dict):
        super().__init__(response_payload)
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.closed = True


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


def test_openai_compatible_provider_uses_configured_proxy_for_real_clients():
    factory = RecordingHttpClientFactory(
        {"choices": [{"message": {"content": "Proxied answer"}}]}
    )
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
    assert factory.clients[0].requests[0]["url"] == "https://api.example.test/v1/chat/completions"
    assert factory.clients[0].closed is True


def test_openai_compatible_provider_reports_non_json_response():
    provider = HttpChatProvider(http_client=NonJsonHttpClient())

    with pytest.raises(
        ProviderCallError,
        match="OpenAI-compatible provider returned non-JSON response",
    ):
        provider.complete(
            ProviderSettings(
                provider="openai_compatible",
                base_url="https://api.example.test/v1",
                model="research-model",
                api_key="secret",
                outbound_context_policy="snippets_only",
            ),
            [ProviderMessage(role="user", content="Question")],
        )


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
