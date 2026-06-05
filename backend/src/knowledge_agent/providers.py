from dataclasses import dataclass
from typing import Protocol

import httpx

from knowledge_agent.models import ProviderSettings


class ProviderCallError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderMessage:
    role: str
    content: str


class ChatProvider(Protocol):
    def complete(
        self,
        settings: ProviderSettings,
        messages: list[ProviderMessage],
    ) -> str:
        pass


class HttpChatProvider:
    def __init__(self, http_client: object | None = None, timeout: float = 60.0) -> None:
        self._http_client = http_client or httpx.Client()
        self._timeout = timeout

    def complete(
        self,
        settings: ProviderSettings,
        messages: list[ProviderMessage],
    ) -> str:
        if settings.provider == "openai_compatible":
            return self._complete_openai_compatible(settings, messages)
        if settings.provider == "ollama":
            return self._complete_ollama(settings, messages)
        raise ProviderCallError(f"unsupported provider: {settings.provider}")

    def _complete_openai_compatible(
        self,
        settings: ProviderSettings,
        messages: list[ProviderMessage],
    ) -> str:
        url = f"{_required_base_url(settings).rstrip('/')}/chat/completions"
        headers = _headers(settings)
        response = self._http_client.post(
            url,
            json={
                "model": _required_model(settings),
                "messages": [_message_payload(message) for message in messages],
                "temperature": 0.2,
            },
            headers=headers,
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()
        try:
            return str(payload["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderCallError("OpenAI-compatible response missing content") from exc

    def _complete_ollama(
        self,
        settings: ProviderSettings,
        messages: list[ProviderMessage],
    ) -> str:
        url = f"{_required_base_url(settings).rstrip('/')}/api/chat"
        response = self._http_client.post(
            url,
            json={
                "model": _required_model(settings),
                "messages": [_message_payload(message) for message in messages],
                "stream": False,
            },
            headers=_headers(settings),
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()
        try:
            return str(payload["message"]["content"])
        except (KeyError, TypeError) as exc:
            raise ProviderCallError("Ollama response missing content") from exc


def _required_base_url(settings: ProviderSettings) -> str:
    if not settings.base_url:
        raise ProviderCallError("provider base_url is required")
    return settings.base_url


def _required_model(settings: ProviderSettings) -> str:
    if not settings.model:
        raise ProviderCallError("provider model is required")
    return settings.model


def _headers(settings: ProviderSettings) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"
    return headers


def _message_payload(message: ProviderMessage) -> dict[str, str]:
    return {"role": message.role, "content": message.content}
