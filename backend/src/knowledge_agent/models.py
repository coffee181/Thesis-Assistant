from dataclasses import dataclass


@dataclass(frozen=True)
class Paper:
    id: int
    title: str
    year: int | None
    doi: str | None
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
