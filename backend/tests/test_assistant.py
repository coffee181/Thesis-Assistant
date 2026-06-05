from pathlib import Path

import pytest

from knowledge_agent.assistant import (
    AssistantConfig,
    ProviderConfigurationError,
    answer_selected_text,
    answer_current_paper_question,
)
from knowledge_agent.db import connect, init_db
from knowledge_agent.models import ChunkInput, ProviderSettings
from knowledge_agent.providers import ProviderMessage
from knowledge_agent.repositories import (
    ChunksRepository,
    DocumentsRepository,
    PapersRepository,
    SettingsRepository,
)


class RecordingChatProvider:
    def __init__(self, answer: str = "模型回答。"):
        self.answer = answer
        self.calls: list[dict[str, object]] = []

    def complete(
        self,
        settings: ProviderSettings,
        messages: list[ProviderMessage],
    ) -> str:
        self.calls.append({"settings": settings, "messages": messages})
        return self.answer


def test_assistant_uses_current_paper_snippets_and_returns_citations(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    provider = RecordingChatProvider("该方法使用检索增强生成，并以引用片段作为依据。")
    with connect(db_path) as conn:
        paper_id = _seed_papers(conn)
        SettingsRepository(conn).save_provider_settings(
            ProviderSettings(
                provider="openai_compatible",
                base_url="https://api.example.test/v1",
                model="research-model",
                api_key="secret",
                outbound_context_policy="snippets_only",
            )
        )

        answer = answer_current_paper_question(
            conn=conn,
            paper_id=paper_id,
            question="What method uses retrieval citations?",
            chat_provider=provider,
            config=AssistantConfig(max_context_chunks=1),
        )

    prompt = provider.calls[0]["messages"][1].content
    assert "Current Paper" in prompt
    assert "Page 2" in prompt
    assert "method uses retrieval grounded citations" in prompt
    assert "Other Paper" not in prompt
    assert "other paper also mentions retrieval" not in prompt
    assert answer.answer == "该方法使用检索增强生成，并以引用片段作为依据。"
    assert answer.mode == "strict"
    assert answer.provider == "openai_compatible"
    assert answer.citations[0].title == "Current Paper"
    assert answer.citations[0].page_number == 2
    assert "method uses retrieval" in answer.citations[0].snippet
    assert answer.citations[0].source_span == "page:2:chars:0-45"


def test_assistant_requires_configured_provider_when_evidence_exists(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        paper_id = _seed_papers(conn)

        with pytest.raises(ProviderConfigurationError):
            answer_current_paper_question(
                conn=conn,
                paper_id=paper_id,
                question="What method is used?",
                chat_provider=RecordingChatProvider(),
            )


def test_assistant_returns_insufficient_evidence_without_calling_provider(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    provider = RecordingChatProvider()
    with connect(db_path) as conn:
        init_db(conn)
        paper = PapersRepository(conn).create(title="Empty Paper", year=None, doi=None)
        DocumentsRepository(conn).create(
            paper_id=paper.id,
            library_path="papers/empty/paper.pdf",
            file_hash="empty",
            page_count=0,
        )
        SettingsRepository(conn).save_provider_settings(
            ProviderSettings(
                provider="openai_compatible",
                base_url="https://api.example.test/v1",
                model="research-model",
                api_key="secret",
                outbound_context_policy="snippets_only",
            )
        )

        answer = answer_current_paper_question(
            conn=conn,
            paper_id=paper.id,
            question="What does this paper say?",
            chat_provider=provider,
        )

    assert provider.calls == []
    assert answer.answer == "当前文献没有可用于回答的已抽取文本。"
    assert answer.citations == []


def test_selected_text_translation_sends_only_selection_to_provider(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    provider = RecordingChatProvider("Selected translation")
    with connect(db_path) as conn:
        paper_id = _seed_papers(conn)
        SettingsRepository(conn).save_provider_settings(
            ProviderSettings(
                provider="openai_compatible",
                base_url="https://api.example.test/v1",
                model="research-model",
                api_key="secret",
                outbound_context_policy="snippets_only",
            )
        )

        answer = answer_selected_text(
            conn=conn,
            paper_id=paper_id,
            selected_text="The selected method uses retrieval augmented generation.",
            page_number=3,
            source_span="page:3:selection",
            action="translate",
            chat_provider=provider,
        )

    prompt = provider.calls[0]["messages"][1].content
    assert "The selected method uses retrieval augmented generation." in prompt
    assert "page:3:selection" in prompt
    assert "Page 3" in prompt
    assert "The introduction discusses background motivation." not in prompt
    assert "The other paper also mentions retrieval" not in prompt
    assert answer.answer == "Selected translation"
    assert answer.mode == "selection"
    assert answer.citations[0].chunk_id is None
    assert answer.citations[0].title == "Current Paper"
    assert answer.citations[0].page_number == 3
    assert answer.citations[0].snippet == "The selected method uses retrieval augmented generation."
    assert answer.citations[0].source_span == "page:3:selection"
    assert answer.qna_id is not None


def test_selected_text_explanation_uses_instruction(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    provider = RecordingChatProvider("Selected explanation")
    with connect(db_path) as conn:
        paper_id = _seed_papers(conn)
        SettingsRepository(conn).save_provider_settings(
            ProviderSettings(
                provider="openai_compatible",
                base_url="https://api.example.test/v1",
                model="research-model",
                api_key="secret",
                outbound_context_policy="snippets_only",
            )
        )

        answer = answer_selected_text(
            conn=conn,
            paper_id=paper_id,
            selected_text="contrastive retrieval",
            page_number=2,
            source_span="page:2:selection",
            action="explain",
            instruction="Explain the term for a first-year graduate student.",
            chat_provider=provider,
        )

    prompt = provider.calls[0]["messages"][1].content
    assert "Action: explain" in prompt
    assert "Explain the term for a first-year graduate student." in prompt
    assert answer.answer == "Selected explanation"
    assert answer.citations[0].snippet == "contrastive retrieval"


def test_selected_text_requires_nonblank_selection(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        paper = PapersRepository(conn).create(title="Readable Paper", year=None, doi=None)

        with pytest.raises(ValueError, match="selected text is required"):
            answer_selected_text(
                conn=conn,
                paper_id=paper.id,
                selected_text="   ",
                page_number=1,
                source_span="page:1:selection",
                action="translate",
                chat_provider=RecordingChatProvider(),
            )


def test_selected_text_requires_configured_provider(tmp_path: Path):
    db_path = tmp_path / "library.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        paper = PapersRepository(conn).create(title="Readable Paper", year=None, doi=None)

        with pytest.raises(ProviderConfigurationError):
            answer_selected_text(
                conn=conn,
                paper_id=paper.id,
                selected_text="important claim",
                page_number=1,
                source_span="page:1:selection",
                action="translate",
                chat_provider=RecordingChatProvider(),
            )


def _seed_papers(conn) -> int:
    init_db(conn)
    papers = PapersRepository(conn)
    documents = DocumentsRepository(conn)
    chunks = ChunksRepository(conn)

    current_paper = papers.create(title="Current Paper", year=2026, doi=None)
    other_paper = papers.create(title="Other Paper", year=2026, doi=None)
    current_document = documents.create(
        paper_id=current_paper.id,
        library_path="papers/current/paper.pdf",
        file_hash="current",
        page_count=2,
    )
    other_document = documents.create(
        paper_id=other_paper.id,
        library_path="papers/other/paper.pdf",
        file_hash="other",
        page_count=1,
    )
    chunks.replace_for_document(
        document_id=current_document.id,
        paper_id=current_paper.id,
        chunks=[
            ChunkInput(
                page_number=1,
                chunk_index=0,
                text="The introduction discusses background motivation.",
                source_span="page:1:chars:0-48",
            ),
            ChunkInput(
                page_number=2,
                chunk_index=0,
                text="The method uses retrieval grounded citations.",
                source_span="page:2:chars:0-45",
            ),
        ],
    )
    chunks.replace_for_document(
        document_id=other_document.id,
        paper_id=other_paper.id,
        chunks=[
            ChunkInput(
                page_number=1,
                chunk_index=0,
                text="The other paper also mentions retrieval grounded citations.",
                source_span="page:1:chars:0-58",
            )
        ],
    )
    return current_paper.id
