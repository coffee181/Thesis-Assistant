from dataclasses import dataclass

from knowledge_agent.models import Chunk, ProviderSettings
from knowledge_agent.providers import ChatProvider, ProviderMessage
from knowledge_agent.repositories import (
    ChunksRepository,
    PapersRepository,
    QnaRepository,
    SettingsRepository,
)


class ProviderConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AssistantConfig:
    max_context_chunks: int = 4


@dataclass(frozen=True)
class TraceableCitation:
    chunk_id: int | None
    paper_id: int
    title: str
    page_number: int
    snippet: str
    source_span: str

    def to_dict(self) -> dict[str, object]:
        return {
            "chunk_id": self.chunk_id,
            "paper_id": self.paper_id,
            "title": self.title,
            "page_number": self.page_number,
            "snippet": self.snippet,
            "source_span": self.source_span,
        }


@dataclass(frozen=True)
class TraceableAnswer:
    answer: str
    citations: list[TraceableCitation]
    mode: str
    provider: str
    qna_id: int | None = None


def answer_current_paper_question(
    conn,
    paper_id: int,
    question: str,
    chat_provider: ChatProvider,
    config: AssistantConfig = AssistantConfig(),
) -> TraceableAnswer:
    paper = PapersRepository(conn).get(paper_id)
    settings = SettingsRepository(conn).get_provider_settings()
    chunks = ChunksRepository(conn).relevant_for_paper(
        paper_id=paper_id,
        query=question,
        limit=config.max_context_chunks,
    )

    if not chunks:
        return TraceableAnswer(
            answer="当前文献没有可用于回答的已抽取文本。",
            citations=[],
            mode="strict",
            provider=settings.provider,
        )

    _ensure_provider_configured(settings)

    citations = [_citation_from_chunk(chunk=chunk, title=paper.title) for chunk in chunks]
    messages = [
        ProviderMessage(
            role="system",
            content=(
                "你是科研文献阅读助手。只根据用户提供的当前论文片段回答。"
                "如果片段不足以支持结论，必须明确说证据不足。"
                "默认使用中文回答，并保留关键英文原文含义。"
            ),
        ),
        ProviderMessage(
            role="user",
            content=_build_prompt(
                paper_title=paper.title,
                question=question,
                citations=citations,
            ),
        ),
    ]
    answer = chat_provider.complete(settings, messages)
    entry = QnaRepository(conn).create(
        paper_id=paper.id,
        question=question,
        answer=answer,
        cited_chunks=[citation.to_dict() for citation in citations],
        mode="strict",
        provider=settings.provider,
    )

    return TraceableAnswer(
        answer=answer,
        citations=citations,
        mode="strict",
        provider=settings.provider,
        qna_id=entry.id,
    )


def answer_selected_text(
    conn,
    paper_id: int,
    selected_text: str,
    page_number: int,
    source_span: str,
    action: str,
    chat_provider: ChatProvider,
    instruction: str | None = None,
) -> TraceableAnswer:
    cleaned_selection = selected_text.strip()
    if not cleaned_selection:
        raise ValueError("selected text is required")
    if action not in {"translate", "explain", "summarize"}:
        raise ValueError("unsupported selected text action")

    paper = PapersRepository(conn).get(paper_id)
    settings = SettingsRepository(conn).get_provider_settings()
    _ensure_provider_configured(settings)

    citation = TraceableCitation(
        chunk_id=None,
        paper_id=paper.id,
        title=paper.title,
        page_number=page_number,
        snippet=cleaned_selection,
        source_span=source_span,
    )
    messages = [
        ProviderMessage(
            role="system",
            content=(
                "You are a research reading assistant. Use only the selected text "
                "provided by the user. Answer in Chinese and preserve important "
                "English technical terms when useful."
            ),
        ),
        ProviderMessage(
            role="user",
            content=_build_selection_prompt(
                paper_title=paper.title,
                action=action,
                selected_text=cleaned_selection,
                page_number=page_number,
                source_span=source_span,
                instruction=instruction,
            ),
        ),
    ]
    answer = chat_provider.complete(settings, messages)
    entry = QnaRepository(conn).create(
        paper_id=paper.id,
        question=f"{action} selected text",
        answer=answer,
        cited_chunks=[citation.to_dict()],
        mode="selection",
        provider=settings.provider,
    )
    return TraceableAnswer(
        answer=answer,
        citations=[citation],
        mode="selection",
        provider=settings.provider,
        qna_id=entry.id,
    )


def _ensure_provider_configured(settings: ProviderSettings) -> None:
    if settings.provider == "none":
        raise ProviderConfigurationError("model provider not configured")
    if settings.outbound_context_policy != "snippets_only":
        raise ProviderConfigurationError("outbound context policy blocks provider calls")
    if not settings.model or not settings.base_url:
        raise ProviderConfigurationError("model provider not configured")


def _citation_from_chunk(chunk: Chunk, title: str) -> TraceableCitation:
    return TraceableCitation(
        chunk_id=chunk.id,
        paper_id=chunk.paper_id,
        title=title,
        page_number=chunk.page_number,
        snippet=chunk.text,
        source_span=chunk.source_span,
    )


def _build_prompt(
    paper_title: str,
    question: str,
    citations: list[TraceableCitation],
) -> str:
    snippets = "\n\n".join(
        (
            f"[S{index}] {citation.title}, Page {citation.page_number}, "
            f"{citation.source_span}\n{citation.snippet}"
        )
        for index, citation in enumerate(citations, start=1)
    )
    return (
        f"Current Paper: {paper_title}\n\n"
        f"Evidence snippets:\n{snippets}\n\n"
        f"Question: {question}\n\n"
        "Answer in Chinese. Cite claims using [S1], [S2] style markers."
    )


def _build_selection_prompt(
    paper_title: str,
    action: str,
    selected_text: str,
    page_number: int,
    source_span: str,
    instruction: str | None,
) -> str:
    extra_instruction = f"\nUser instruction: {instruction.strip()}" if instruction else ""
    return (
        f"Current Paper: {paper_title}\n"
        f"Action: {action}\n"
        f"Source: Page {page_number}, {source_span}\n\n"
        f"Selected text:\n{selected_text}\n"
        f"{extra_instruction}\n\n"
        "Return a concise Chinese response grounded only in the selected text. "
        "Refer to the source as [Selection]."
    )
