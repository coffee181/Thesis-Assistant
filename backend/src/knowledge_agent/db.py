import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma foreign_keys = on")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        create table if not exists papers (
            id integer primary key autoincrement,
            title text not null,
            authors text,
            year integer,
            doi text,
            venue text,
            abstract text,
            citation_key text,
            arxiv_id text,
            entry_type text,
            created_at text not null default current_timestamp
        );

        create unique index if not exists idx_papers_doi_unique
        on papers(doi)
        where doi is not null;

        create table if not exists documents (
            id integer primary key autoincrement,
            paper_id integer not null references papers(id) on delete cascade,
            library_path text not null,
            file_hash text not null unique,
            page_count integer,
            parse_status text not null default 'pending',
            parse_error text,
            created_at text not null default current_timestamp
        );

        create table if not exists chunks (
            id integer primary key autoincrement,
            paper_id integer not null references papers(id) on delete cascade,
            document_id integer not null references documents(id) on delete cascade,
            page_number integer not null,
            chunk_index integer not null,
            text text not null,
            source_span text not null,
            created_at text not null default current_timestamp,
            unique(document_id, page_number, chunk_index)
        );

        create virtual table if not exists chunks_fts using fts5(
            text,
            paper_title,
            paper_id unindexed,
            document_id unindexed,
            chunk_id unindexed,
            page_number unindexed
        );

        create table if not exists settings (
            key text primary key,
            value text not null,
            updated_at text not null default current_timestamp
        );

        create table if not exists qna_entries (
            id integer primary key autoincrement,
            paper_id integer not null references papers(id) on delete cascade,
            question text not null,
            answer text not null,
            cited_chunks text not null,
            mode text not null,
            provider text not null,
            created_at text not null default current_timestamp
        );
        """
    )
    _ensure_column(
        conn,
        table_name="documents",
        column_name="parse_status",
        definition="parse_status text not null default 'pending'",
    )
    _ensure_column(
        conn,
        table_name="documents",
        column_name="parse_error",
        definition="parse_error text",
    )
    for column_name, definition in [
        ("authors", "authors text"),
        ("venue", "venue text"),
        ("abstract", "abstract text"),
        ("citation_key", "citation_key text"),
        ("arxiv_id", "arxiv_id text"),
        ("entry_type", "entry_type text"),
    ]:
        _ensure_column(
            conn,
            table_name="papers",
            column_name=column_name,
            definition=definition,
        )
    conn.execute(
        """
        create unique index if not exists idx_papers_citation_key_unique
        on papers(citation_key)
        where citation_key is not null
        """
    )


def _ensure_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    columns = {
        row["name"]
        for row in conn.execute(f"pragma table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        conn.execute(f"alter table {table_name} add column {definition}")
