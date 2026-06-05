import sqlite3

from knowledge_agent.models import Document, Paper


class PapersRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, title: str, year: int | None, doi: str | None) -> Paper:
        cursor = self._conn.execute(
            "insert into papers (title, year, doi) values (?, ?, ?)",
            (title, year, doi),
        )
        return self.get(cursor.lastrowid)

    def get(self, paper_id: int) -> Paper:
        row = self._conn.execute(
            "select id, title, year, doi, created_at from papers where id = ?",
            (paper_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"paper not found: {paper_id}")
        return Paper(**dict(row))

    def list_all(self) -> list[Paper]:
        rows = self._conn.execute(
            "select id, title, year, doi, created_at from papers order by created_at desc, id desc"
        ).fetchall()
        return [Paper(**dict(row)) for row in rows]


class DocumentsRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        paper_id: int,
        library_path: str,
        file_hash: str,
        page_count: int | None,
    ) -> Document:
        cursor = self._conn.execute(
            """
            insert into documents (paper_id, library_path, file_hash, page_count)
            values (?, ?, ?, ?)
            """,
            (paper_id, library_path, file_hash, page_count),
        )
        return self.get(cursor.lastrowid)

    def get(self, document_id: int) -> Document:
        row = self._conn.execute(
            """
            select id, paper_id, library_path, file_hash, page_count, created_at
            from documents
            where id = ?
            """,
            (document_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"document not found: {document_id}")
        return Document(**dict(row))

    def find_by_hash(self, file_hash: str) -> Document | None:
        row = self._conn.execute(
            """
            select id, paper_id, library_path, file_hash, page_count, created_at
            from documents
            where file_hash = ?
            """,
            (file_hash,),
        ).fetchone()
        return Document(**dict(row)) if row else None
