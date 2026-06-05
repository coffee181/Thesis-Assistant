from dataclasses import dataclass, field


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
    favorite: bool = False
    tags: list[str] = field(default_factory=list)


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
class Job:
    id: int
    kind: str
    status: str
    source_path: str
    description: str | None
    total_items: int
    processed_items: int
    succeeded_items: int
    failed_items: int
    error: str | None
    result_json: str | None
    created_at: str
    updated_at: str


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
    document_id: int | None
    chunk_id: int | None
    page_number: int | None
    snippet: str


@dataclass(frozen=True)
class PublicProviderSettings:
    provider: str
    base_url: str | None
    model: str | None
    outbound_context_policy: str
    proxy_url: str | None
    api_key_configured: bool
    api_key: None = None


@dataclass(frozen=True)
class ProviderSettings:
    provider: str = "none"
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    outbound_context_policy: str = "snippets_only"
    proxy_url: str | None = None

    def to_public(self) -> PublicProviderSettings:
        return PublicProviderSettings(
            provider=self.provider,
            base_url=self.base_url,
            model=self.model,
            outbound_context_policy=self.outbound_context_policy,
            proxy_url=self.proxy_url,
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
