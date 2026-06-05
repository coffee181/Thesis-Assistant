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
            favorite integer not null default 0,
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

        create table if not exists chunk_vectors (
            chunk_id integer primary key references chunks(id) on delete cascade,
            paper_id integer not null references papers(id) on delete cascade,
            document_id integer not null references documents(id) on delete cascade,
            vector_id text not null unique,
            embedding_model text not null,
            updated_at text not null default current_timestamp
        );

        create index if not exists idx_chunk_vectors_document_id
        on chunk_vectors(document_id);

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

        create table if not exists search_results (
            id integer primary key autoincrement,
            query text not null,
            source text not null,
            external_id text not null,
            title text not null,
            authors text,
            year integer,
            doi text,
            venue text,
            abstract text,
            arxiv_id text,
            pdf_url text,
            landing_url text,
            created_at text not null default current_timestamp,
            unique(source, external_id)
        );

        create index if not exists idx_search_results_query
        on search_results(query);

        create table if not exists notes (
            id integer primary key autoincrement,
            paper_id integer not null references papers(id) on delete cascade,
            body text not null,
            page_number integer,
            source_span text,
            selected_text text,
            note_type text not null default 'manual',
            qna_id integer references qna_entries(id) on delete set null,
            created_at text not null default current_timestamp,
            updated_at text not null default current_timestamp
        );

        create index if not exists idx_notes_paper_id
        on notes(paper_id);

        create table if not exists highlights (
            id integer primary key autoincrement,
            paper_id integer not null references papers(id) on delete cascade,
            page_number integer not null,
            source_span text not null,
            selected_text text not null,
            color text not null default 'yellow',
            note_id integer references notes(id) on delete set null,
            created_at text not null default current_timestamp
        );

        create index if not exists idx_highlights_paper_id
        on highlights(paper_id);

        create table if not exists tags (
            id integer primary key autoincrement,
            name text not null unique,
            created_at text not null default current_timestamp
        );

        create table if not exists paper_tags (
            paper_id integer not null references papers(id) on delete cascade,
            tag_id integer not null references tags(id) on delete cascade,
            created_at text not null default current_timestamp,
            primary key (paper_id, tag_id)
        );

        create index if not exists idx_paper_tags_tag_id
        on paper_tags(tag_id);

        create table if not exists jobs (
            id integer primary key autoincrement,
            kind text not null,
            status text not null,
            source_path text not null,
            description text,
            total_items integer not null default 0,
            processed_items integer not null default 0,
            succeeded_items integer not null default 0,
            failed_items integer not null default 0,
            error text,
            result_json text,
            created_at text not null default current_timestamp,
            updated_at text not null default current_timestamp
        );

        create index if not exists idx_jobs_created_at
        on jobs(created_at, id);
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
        ("favorite", "favorite integer not null default 0"),
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
