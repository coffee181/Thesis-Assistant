from dataclasses import dataclass


@dataclass(frozen=True)
class Paper:
    id: int
    title: str
    authors: str | None
    year: int | None
    doi: str | None
    venue: str | None
    abstract: str | None
    citation_key: str | None
    arxiv_id: str | None
    entry_type: str | None
    created_at: str


@dataclass(frozen=True)
class BibliographyRecord:
    citation_key: str | None
    title: str
    authors: str | None
    year: int | None
    doi: str | None
    venue: str | None
    abstract: str | None
    arxiv_id: str | None
    entry_type: str | None


@dataclass(frozen=True)
class DiscoveryCandidate:
    source: str
    external_id: str
    title: str
    authors: str | None
    year: int | None
    doi: str | None
    venue: str | None
    abstract: str | None
    arxiv_id: str | None
    pdf_url: str | None
    landing_url: str | None


@dataclass(frozen=True)
class SearchResultRecord:
    id: int
    query: str
    source: str
    external_id: str
    title: str
    authors: str | None
    year: int | None
    doi: str | None
    venue: str | None
    abstract: str | None
    arxiv_id: str | None
    pdf_url: str | None
    landing_url: str | None
    created_at: str


@dataclass(frozen=True)
class Note:
    id: int
    paper_id: int
    body: str
    page_number: int | None
    source_span: str | None
    selected_text: str | None
    note_type: str
    qna_id: int | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Highlight:
    id: int
    paper_id: int
    page_number: int
    source_span: str
    selected_text: str
    color: str
    note_id: int | None
    created_at: str


@dataclass(frozen=True)
class Document:
    id: int
    paper_id: int
    library_path: str
    file_hash: str
    page_count: int | None
    parse_status: str
    parse_error: str | None
    created_at: str


@dataclass(frozen=True)
class ChunkInput:
    page_number: int
    chunk_index: int
    text: str
    source_span: str


@dataclass(frozen=True)
class Chunk:
    id: int
    paper_id: int
    document_id: int
    page_number: int
    chunk_index: int
    text: str
    source_span: str
    created_at: str


@dataclass(frozen=True)
class SearchHit:
    paper_id: int
    title: str
    year: int | None
    doi: str | None
    document_id: int
    chunk_id: int
    page_number: int
    snippet: str


@dataclass(frozen=True)
class PublicProviderSettings:
    provider: str
    base_url: str | None
    model: str | None
    outbound_context_policy: str
    api_key_configured: bool
    api_key: None = None


@dataclass(frozen=True)
class ProviderSettings:
    provider: str = "none"
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    outbound_context_policy: str = "snippets_only"

    def to_public(self) -> PublicProviderSettings:
        return PublicProviderSettings(
            provider=self.provider,
            base_url=self.base_url,
            model=self.model,
            outbound_context_policy=self.outbound_context_policy,
            api_key_configured=bool(self.api_key),
        )


@dataclass(frozen=True)
class QnaEntry:
    id: int
    paper_id: int
    question: str
    answer: str
    cited_chunks: list[dict[str, object]]
    mode: str
    provider: str
    created_at: str
