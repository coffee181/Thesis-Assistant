from pydantic import BaseModel, ConfigDict, Field


class PaperResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    year: int | None
    doi: str | None
    created_at: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paper_id: int
    library_path: str
    file_hash: str
    page_count: int | None
    parse_status: str
    parse_error: str | None
    created_at: str


class ImportPdfRequest(BaseModel):
    source_path: str = Field(min_length=1)


class ImportPdfResponse(BaseModel):
    imported: bool
    paper: PaperResponse
    document: DocumentResponse


class PapersResponse(BaseModel):
    papers: list[PaperResponse]


class SearchHitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    paper_id: int
    title: str
    year: int | None
    doi: str | None
    document_id: int
    chunk_id: int
    page_number: int
    snippet: str


class LocalSearchResponse(BaseModel):
    query: str
    hits: list[SearchHitResponse]


class ReaderPageResponse(BaseModel):
    page_number: int
    text: str


class ReaderContextResponse(BaseModel):
    paper: PaperResponse
    document: DocumentResponse
    pages: list[ReaderPageResponse]


class ProviderSettingsRequest(BaseModel):
    provider: str = Field(pattern="^(none|openai_compatible|ollama)$")
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    outbound_context_policy: str = Field(
        default="snippets_only",
        pattern="^(snippets_only|local_only)$",
    )


class ProviderSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    base_url: str | None
    model: str | None
    outbound_context_policy: str
    api_key_configured: bool


class AskPaperQuestionRequest(BaseModel):
    question: str = Field(min_length=1)


class CitationResponse(BaseModel):
    chunk_id: int
    paper_id: int
    title: str
    page_number: int
    snippet: str
    source_span: str


class AskPaperQuestionResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
    mode: str
    provider: str
    qna_id: int | None
