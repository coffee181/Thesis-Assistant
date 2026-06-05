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
            year integer,
            doi text,
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
            created_at text not null default current_timestamp
        );
        """
    )
