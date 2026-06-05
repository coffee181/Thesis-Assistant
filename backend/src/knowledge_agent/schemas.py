from pydantic import BaseModel, ConfigDict, Field


class PaperResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class LibraryResponse(BaseModel):
    library_dir: str
    database_path: str
    paper_count: int


class SelectLibraryRequest(BaseModel):
    library_dir: str = Field(min_length=1)


class ImportFolderRequest(BaseModel):
    source_dir: str = Field(min_length=1)


class ImportFolderFailureResponse(BaseModel):
    source_path: str
    error: str


class ImportFolderResponse(BaseModel):
    source_path: str
    discovered_count: int
    imported_count: int
    skipped_count: int
    failed_count: int
    imports: list[ImportPdfResponse]
    failures: list[ImportFolderFailureResponse]


class ImportBibliographyRequest(BaseModel):
    source_path: str = Field(min_length=1)
    format: str | None = Field(default=None, pattern="^(auto|bib|bibtex|ris)$")


class ImportBibliographyResponse(BaseModel):
    format: str
    imported_count: int
    updated_count: int
    papers: list[PaperResponse]


class ExportBibliographyResponse(BaseModel):
    format: str
    content: str


class PapersResponse(BaseModel):
    papers: list[PaperResponse]


class SearchResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ExternalSearchResponse(BaseModel):
    query: str
    results: list[SearchResultResponse]


class OpenPdfDownloadRequest(BaseModel):
    search_result_id: int


class OpenPdfDownloadResponse(BaseModel):
    pending_path: str
    result: SearchResultResponse


class ImportPendingDownloadRequest(BaseModel):
    search_result_id: int
    pending_path: str = Field(min_length=1)


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


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class NotesResponse(BaseModel):
    notes: list[NoteResponse]


class HighlightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paper_id: int
    page_number: int
    source_span: str
    selected_text: str
    color: str
    note_id: int | None
    created_at: str


class HighlightsResponse(BaseModel):
    highlights: list[HighlightResponse]


class CreateNoteRequest(BaseModel):
    paper_id: int
    body: str = Field(min_length=1)
    page_number: int | None = None
    source_span: str | None = None
    selected_text: str | None = None
    note_type: str = Field(
        default="manual",
        pattern="^(manual|assistant_answer|selection)$",
    )
    qna_id: int | None = None


class CreateHighlightRequest(BaseModel):
    paper_id: int
    page_number: int
    source_span: str = Field(min_length=1)
    selected_text: str = Field(min_length=1)
    color: str = "yellow"
    note_id: int | None = None


class ProviderSettingsRequest(BaseModel):
    provider: str = Field(pattern="^(none|openai_compatible|ollama)$")
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    outbound_context_policy: str = Field(
        default="snippets_only",
        pattern="^(snippets_only|local_only)$",
    )
    proxy_url: str | None = None


class ProviderSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    base_url: str | None
    model: str | None
    outbound_context_policy: str
    proxy_url: str | None
    api_key_configured: bool


class AskPaperQuestionRequest(BaseModel):
    question: str = Field(min_length=1)


class SelectedTextAssistantRequest(BaseModel):
    selected_text: str = Field(min_length=1)
    page_number: int
    source_span: str = Field(min_length=1)
    action: str = Field(pattern="^(translate|explain|summarize)$")
    instruction: str | None = None


class CitationResponse(BaseModel):
    chunk_id: int | None
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
