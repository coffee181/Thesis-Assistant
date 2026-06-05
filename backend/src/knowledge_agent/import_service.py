import hashlib
import re
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from knowledge_agent.models import Document, Paper
from knowledge_agent.repositories import DocumentsRepository, PapersRepository


@dataclass(frozen=True)
class ImportResult:
    paper: Paper
    document: Document
    imported: bool


def import_pdf(conn: sqlite3.Connection, library_root: Path, source_path: Path) -> ImportResult:
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
        return ImportResult(
            paper=papers.get(existing.paper_id),
            document=existing,
            imported=False,
        )

    title = source_path.stem.strip()
    paper = papers.create(title=title, year=None, doi=None)
    target_relative = _target_relative_path(paper.id, title, file_hash)
    target_absolute = library_root / target_relative
    target_absolute.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_absolute)

    document = documents.create(
        paper_id=paper.id,
        library_path=target_relative.as_posix(),
        file_hash=file_hash,
        page_count=None,
    )
    return ImportResult(paper=paper, document=document, imported=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _target_relative_path(paper_id: int, title: str, file_hash: str) -> Path:
    slug = _slugify(title) or "untitled"
    short_hash = file_hash[:12]
    return Path("papers") / "unknown-year" / f"{slug}-{paper_id}-{short_hash}" / "paper.pdf"


def _slugify(value: str) -> str:
    lowered = value.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    return normalized.strip("-")
