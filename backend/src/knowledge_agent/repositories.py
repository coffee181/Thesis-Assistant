import sqlite3

from knowledge_agent.models import Chunk, ChunkInput, Document, Paper, SearchHit


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
            select
                id,
                paper_id,
                library_path,
                file_hash,
                page_count,
                parse_status,
                parse_error,
                created_at
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
            select
                id,
                paper_id,
                library_path,
                file_hash,
                page_count,
                parse_status,
                parse_error,
                created_at
            from documents
            where file_hash = ?
            """,
            (file_hash,),
        ).fetchone()
        return Document(**dict(row)) if row else None

    def find_by_paper_id(self, paper_id: int) -> Document | None:
        row = self._conn.execute(
            """
            select
                id,
                paper_id,
                library_path,
                file_hash,
                page_count,
                parse_status,
                parse_error,
                created_at
            from documents
            where paper_id = ?
            order by created_at desc, id desc
            limit 1
            """,
            (paper_id,),
        ).fetchone()
        return Document(**dict(row)) if row else None

    def update_parse_result(
        self,
        document_id: int,
        page_count: int | None,
        parse_status: str,
        parse_error: str | None,
    ) -> Document:
        self._conn.execute(
            """
            update documents
            set page_count = ?, parse_status = ?, parse_error = ?
            where id = ?
            """,
            (page_count, parse_status, parse_error, document_id),
        )
        return self.get(document_id)


class ChunksRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def replace_for_document(
        self,
        document_id: int,
        paper_id: int,
        chunks: list[ChunkInput],
    ) -> list[Chunk]:
        paper_title = self._paper_title(paper_id)
        self._conn.execute("delete from chunks_fts where document_id = ?", (document_id,))
        self._conn.execute("delete from chunks where document_id = ?", (document_id,))

        for chunk in chunks:
            cursor = self._conn.execute(
                """
                insert into chunks (
                    paper_id,
                    document_id,
                    page_number,
                    chunk_index,
                    text,
                    source_span
                )
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    paper_id,
                    document_id,
                    chunk.page_number,
                    chunk.chunk_index,
                    chunk.text,
                    chunk.source_span,
                ),
            )
            chunk_id = cursor.lastrowid
            self._conn.execute(
                """
                insert into chunks_fts (
                    rowid,
                    text,
                    paper_title,
                    paper_id,
                    document_id,
                    chunk_id,
                    page_number
                )
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk_id,
                    chunk.text,
                    paper_title,
                    paper_id,
                    document_id,
                    chunk_id,
                    chunk.page_number,
                ),
            )

        return self.list_for_paper(paper_id)

    def list_for_paper(self, paper_id: int) -> list[Chunk]:
        rows = self._conn.execute(
            """
            select
                id,
                paper_id,
                document_id,
                page_number,
                chunk_index,
                text,
                source_span,
                created_at
            from chunks
            where paper_id = ?
            order by page_number asc, chunk_index asc, id asc
            """,
            (paper_id,),
        ).fetchall()
        return [Chunk(**dict(row)) for row in rows]

    def search(self, query: str, limit: int = 25) -> list[SearchHit]:
        normalized_query = query.strip()
        if not normalized_query:
            return []
        rows = self._conn.execute(
            """
            select
                cast(chunks_fts.paper_id as integer) as paper_id,
                papers.title as title,
                papers.year as year,
                papers.doi as doi,
                cast(chunks_fts.document_id as integer) as document_id,
                cast(chunks_fts.chunk_id as integer) as chunk_id,
                cast(chunks_fts.page_number as integer) as page_number,
                chunks_fts.text as snippet
            from chunks_fts
            join papers on papers.id = cast(chunks_fts.paper_id as integer)
            where chunks_fts match ?
            order by rank
            limit ?
            """,
            (_fts_phrase(normalized_query), limit),
        ).fetchall()
        return [SearchHit(**dict(row)) for row in rows]

    def _paper_title(self, paper_id: int) -> str:
        row = self._conn.execute(
            "select title from papers where id = ?",
            (paper_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"paper not found: {paper_id}")
        return str(row["title"])


def _fts_phrase(query: str) -> str:
    escaped = query.replace('"', '""')
    return f'"{escaped}"'
