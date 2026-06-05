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
    created_at: str


class ImportPdfRequest(BaseModel):
    source_path: str = Field(min_length=1)


class ImportPdfResponse(BaseModel):
    imported: bool
    paper: PaperResponse
    document: DocumentResponse


class PapersResponse(BaseModel):
    papers: list[PaperResponse]
