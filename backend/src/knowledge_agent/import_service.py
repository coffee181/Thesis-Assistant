import hashlib
import re
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from knowledge_agent.models import BibliographyRecord, Document, Paper
from knowledge_agent.pdf_text import chunk_pages, extract_pdf_pages
from knowledge_agent.repositories import ChunksRepository, DocumentsRepository, PapersRepository


@dataclass(frozen=True)
class ImportResult:
    paper: Paper
    document: Document
    imported: bool


@dataclass(frozen=True)
class FolderImportFailure:
    source_path: str
    error: str


@dataclass(frozen=True)
class FolderImportResult:
    source_path: str
    discovered_count: int
    imported_count: int
    skipped_count: int
    failed_count: int
    imports: list[ImportResult]
    failures: list[FolderImportFailure]


def import_pdf(
    conn: sqlite3.Connection,
    library_root: Path,
    source_path: Path,
    metadata: BibliographyRecord | None = None,
) -> ImportResult:
    source_path = source_path.resolve()
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    if source_path.suffix.lower() != ".pdf":
        raise ValueError("only PDF files can be imported")

    file_hash = _sha256(source_path)
    papers = PapersRepository(conn)
    documents = DocumentsRepository(conn)

    existing = documents.find_by_hash(file_hash)
    if existing is not None:
        paper = papers.get(existing.paper_id)
        if metadata is not None:
            metadata_paper = papers.find_by_metadata(metadata)
            if metadata_paper is not None and metadata_paper.id != existing.paper_id:
                papers.merge_papers(
                    source_paper_id=existing.paper_id,
                    target_paper_id=metadata_paper.id,
                )
                existing = documents.get(existing.id)
                paper = papers.update_metadata(metadata_paper.id, metadata)
            else:
                paper = papers.update_metadata(existing.paper_id, metadata)
        return ImportResult(
            paper=paper,
            document=existing,
            imported=False,
        )

    if metadata is not None:
        existing_paper = papers.find_by_metadata(metadata)
        paper = (
            papers.update_metadata(existing_paper.id, metadata)
            if existing_paper is not None
            else papers.create(
                title=metadata.title,
                year=metadata.year,
                doi=metadata.doi,
                authors=metadata.authors,
                venue=metadata.venue,
                abstract=metadata.abstract,
                citation_key=metadata.citation_key,
                arxiv_id=metadata.arxiv_id,
                entry_type=metadata.entry_type,
            )
        )
    else:
        title = source_path.stem.strip()
        paper = papers.create(
            title=title,
            year=None,
            doi=None,
            authors=None,
            venue=None,
            abstract=None,
            citation_key=None,
            arxiv_id=None,
            entry_type=None,
        )

    target_relative = _target_relative_path(
        paper.id,
        paper.title,
        file_hash,
        paper.year,
    )
    target_absolute = library_root / target_relative
    target_absolute.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_absolute)

    document = documents.create(
        paper_id=paper.id,
        library_path=target_relative.as_posix(),
        file_hash=file_hash,
        page_count=None,
    )
    document = _parse_imported_document(
        conn=conn,
        library_root=library_root,
        paper=paper,
        document=document,
    )
    return ImportResult(paper=paper, document=document, imported=True)


def import_pdf_folder(
    conn: sqlite3.Connection,
    library_root: Path,
    source_dir: Path,
) -> FolderImportResult:
    source_dir = source_dir.resolve()
    if not source_dir.exists():
        raise FileNotFoundError(source_dir)
    if not source_dir.is_dir():
        raise ValueError("source path is not a folder")

    pdf_paths = sorted(
        (path for path in source_dir.rglob("*") if path.suffix.lower() == ".pdf"),
        key=lambda path: path.as_posix().lower(),
    )
    imports: list[ImportResult] = []
    failures: list[FolderImportFailure] = []
    imported_count = 0
    skipped_count = 0

    for pdf_path in pdf_paths:
        try:
            result = import_pdf(conn, library_root, pdf_path)
        except Exception as exc:
            failures.append(
                FolderImportFailure(
                    source_path=str(pdf_path),
                    error=str(exc)[:500],
                )
            )
            continue

        if result.imported:
            imports.append(result)
            imported_count += 1
        else:
            skipped_count += 1

    return FolderImportResult(
        source_path=str(source_dir),
        discovered_count=len(pdf_paths),
        imported_count=imported_count,
        skipped_count=skipped_count,
        failed_count=len(failures),
        imports=imports,
        failures=failures,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _target_relative_path(
    paper_id: int,
    title: str,
    file_hash: str,
    year: int | None,
) -> Path:
    slug = _slugify(title) or "untitled"
    short_hash = file_hash[:12]
    year_folder = str(year) if year is not None else "unknown-year"
    return Path("papers") / year_folder / f"{slug}-{paper_id}-{short_hash}" / "paper.pdf"


def _slugify(value: str) -> str:
    lowered = value.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    return normalized.strip("-")


def _parse_imported_document(
    conn: sqlite3.Connection,
    library_root: Path,
    paper: Paper,
    document: Document,
) -> Document:
    documents = DocumentsRepository(conn)
    try:
        pages = extract_pdf_pages(library_root / document.library_path)
        chunks = chunk_pages(pages)
        ChunksRepository(conn).replace_for_document(
            document_id=document.id,
            paper_id=paper.id,
            chunks=chunks,
        )
        return documents.update_parse_result(
            document_id=document.id,
            page_count=len(pages),
            parse_status="parsed",
            parse_error=None,
        )
    except Exception as exc:
        return documents.update_parse_result(
            document_id=document.id,
            page_count=None,
            parse_status="failed",
            parse_error=str(exc)[:500],
        )
