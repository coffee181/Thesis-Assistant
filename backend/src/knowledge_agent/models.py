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
    created_at: str
