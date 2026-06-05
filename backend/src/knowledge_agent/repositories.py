import json
import re
import sqlite3

from knowledge_agent.models import (
    BibliographyRecord,
    Chunk,
    ChunkInput,
    Document,
    DiscoveryCandidate,
    Highlight,
    Note,
    Paper,
    ProviderSettings,
    QnaEntry,
    SearchResultRecord,
    SearchHit,
)


PROVIDER_SETTINGS_KEY = "provider_settings"


class PapersRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        title: str,
        year: int | None,
        doi: str | None,
        authors: str | None = None,
        venue: str | None = None,
        abstract: str | None = None,
        citation_key: str | None = None,
        arxiv_id: str | None = None,
        entry_type: str | None = None,
    ) -> Paper:
        cursor = self._conn.execute(
            """
            insert into papers (
                title,
                authors,
                year,
                doi,
                venue,
                abstract,
                citation_key,
                arxiv_id,
                entry_type
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                authors,
                year,
                _normalize_doi(doi),
                venue,
                abstract,
                citation_key,
                arxiv_id,
                entry_type,
            ),
        )
        return self.get(cursor.lastrowid)

    def get(self, paper_id: int) -> Paper:
        row = self._conn.execute(
            """
            select
                id,
                title,
                authors,
                year,
                doi,
                venue,
                abstract,
                citation_key,
                arxiv_id,
                entry_type,
                favorite,
                created_at
            from papers
            where id = ?
            """,
            (paper_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"paper not found: {paper_id}")
        return self._paper_from_row(row)

    def list_all(
        self,
        favorite: bool | None = None,
        tag: str | None = None,
    ) -> list[Paper]:
        filters = []
        params: list[object] = []
        if favorite is not None:
            filters.append("papers.favorite = ?")
            params.append(1 if favorite else 0)
        tag_name = _normalize_tag_name(tag)
        if tag_name is not None:
            filters.append(
                """
                exists (
                    select 1
                    from paper_tags
                    join tags on tags.id = paper_tags.tag_id
                    where paper_tags.paper_id = papers.id and tags.name = ?
                )
                """
            )
            params.append(tag_name)
        where_clause = f"where {' and '.join(filters)}" if filters else ""
        rows = self._conn.execute(
            """
            select
                id,
                title,
                authors,
                year,
                doi,
                venue,
                abstract,
                citation_key,
                arxiv_id,
                entry_type,
                favorite,
                created_at
            from papers
            {where_clause}
            order by created_at desc, id desc
            """.format(where_clause=where_clause),
            params,
        ).fetchall()
        return [self._paper_from_row(row) for row in rows]

    def upsert_metadata(self, record: BibliographyRecord) -> Paper:
        existing = self.find_by_metadata(record)
        if existing is None:
            return self.create(
                title=record.title,
                authors=record.authors,
                year=record.year,
                doi=record.doi,
                venue=record.venue,
                abstract=record.abstract,
                citation_key=record.citation_key,
                arxiv_id=record.arxiv_id,
                entry_type=record.entry_type,
            )

        self._conn.execute(
            """
            update papers
            set
                title = ?,
                authors = ?,
                year = ?,
                doi = ?,
                venue = ?,
                abstract = ?,
                citation_key = ?,
                arxiv_id = ?,
                entry_type = ?
            where id = ?
            """,
            (
                record.title,
                record.authors,
                record.year,
                _normalize_doi(record.doi),
                record.venue,
                record.abstract,
                record.citation_key,
                record.arxiv_id,
                record.entry_type,
                existing.id,
            ),
        )
        return self.get(existing.id)

    def update_metadata(self, paper_id: int, record: BibliographyRecord) -> Paper:
        self._conn.execute(
            """
            update papers
            set
                title = ?,
                authors = ?,
                year = ?,
                doi = ?,
                venue = ?,
                abstract = ?,
                citation_key = ?,
                arxiv_id = ?,
                entry_type = ?
            where id = ?
            """,
            (
                record.title,
                record.authors,
                record.year,
                _normalize_doi(record.doi),
                record.venue,
                record.abstract,
                record.citation_key,
                record.arxiv_id,
                record.entry_type,
                paper_id,
            ),
        )
        self._rebuild_fts_for_paper(paper_id)
        return self.get(paper_id)

    def merge_papers(self, source_paper_id: int, target_paper_id: int) -> Paper:
        if source_paper_id == target_paper_id:
            return self.get(target_paper_id)

        source_paper = self.get(source_paper_id)
        target_paper = self.get(target_paper_id)
        if source_paper.favorite and not target_paper.favorite:
            self._conn.execute(
                "update papers set favorite = 1 where id = ?",
                (target_paper_id,),
            )
        self._conn.execute(
            """
            insert into paper_tags (paper_id, tag_id)
            select ?, tag_id
            from paper_tags
            where paper_id = ?
            on conflict(paper_id, tag_id) do nothing
            """,
            (target_paper_id, source_paper_id),
        )
        self._conn.execute(
            "delete from paper_tags where paper_id = ?",
            (source_paper_id,),
        )
        for table_name in ("documents", "chunks", "notes", "highlights", "qna_entries"):
            self._conn.execute(
                f"update {table_name} set paper_id = ? where paper_id = ?",
                (target_paper_id, source_paper_id),
            )
        self._conn.execute("delete from papers where id = ?", (source_paper_id,))
        self._rebuild_fts_for_paper(target_paper_id)
        return self.get(target_paper_id)

    def find_by_metadata(
        self,
        record: BibliographyRecord,
    ) -> Paper | None:
        normalized_doi = _normalize_doi(record.doi)
        if normalized_doi:
            row = self._conn.execute(
                """
                select
                    id,
                    title,
                    authors,
                    year,
                    doi,
                    venue,
                    abstract,
                citation_key,
                arxiv_id,
                entry_type,
                favorite,
                created_at
                from papers
                where doi = ?
                """,
                (normalized_doi,),
            ).fetchone()
            if row is not None:
                return self._paper_from_row(row)

        if record.citation_key:
            row = self._conn.execute(
                """
                select
                    id,
                    title,
                    authors,
                    year,
                    doi,
                    venue,
                    abstract,
                    citation_key,
                    arxiv_id,
                    entry_type,
                    favorite,
                    created_at
                from papers
                where citation_key = ?
                """,
                (record.citation_key,),
            ).fetchone()
            if row is not None:
                return self._paper_from_row(row)

        row = self._conn.execute(
            """
            select
                id,
                title,
                authors,
                year,
                doi,
                venue,
                abstract,
                citation_key,
                arxiv_id,
                entry_type,
                favorite,
                created_at
            from papers
            where lower(title) = lower(?) and ((year is null and ? is null) or year = ?)
            """,
            (record.title, record.year, record.year),
        ).fetchone()
        return self._paper_from_row(row) if row is not None else None

    def set_favorite(self, paper_id: int, favorite: bool) -> Paper:
        self.get(paper_id)
        self._conn.execute(
            "update papers set favorite = ? where id = ?",
            (1 if favorite else 0, paper_id),
        )
        return self.get(paper_id)

    def add_tag(self, paper_id: int, tag_name: str) -> Paper:
        self.get(paper_id)
        name = _normalize_tag_name(tag_name)
        if name is None:
            raise ValueError("tag name is required")
        self._conn.execute(
            """
            insert into tags (name)
            values (?)
            on conflict(name) do nothing
            """,
            (name,),
        )
        row = self._conn.execute(
            "select id from tags where name = ?",
            (name,),
        ).fetchone()
        if row is None:
            raise RuntimeError("tag insert failed")
        self._conn.execute(
            """
            insert into paper_tags (paper_id, tag_id)
            values (?, ?)
            on conflict(paper_id, tag_id) do nothing
            """,
            (paper_id, row["id"]),
        )
        return self.get(paper_id)

    def remove_tag(self, paper_id: int, tag_name: str) -> Paper:
        self.get(paper_id)
        name = _normalize_tag_name(tag_name)
        if name is None:
            raise ValueError("tag name is required")
        self._conn.execute(
            """
            delete from paper_tags
            where paper_id = ?
              and tag_id in (select id from tags where name = ?)
            """,
            (paper_id, name),
        )
        return self.get(paper_id)

    def _paper_from_row(self, row: sqlite3.Row) -> Paper:
        payload = dict(row)
        payload["favorite"] = bool(payload.get("favorite", 0))
        payload["tags"] = self._tags_for_paper(int(payload["id"]))
        return Paper(**payload)

    def _tags_for_paper(self, paper_id: int) -> list[str]:
        rows = self._conn.execute(
            """
            select tags.name
            from paper_tags
            join tags on tags.id = paper_tags.tag_id
            where paper_tags.paper_id = ?
            order by lower(tags.name), tags.name
            """,
            (paper_id,),
        ).fetchall()
        return [str(row["name"]) for row in rows]

    def _rebuild_fts_for_paper(self, paper_id: int) -> None:
        rows = self._conn.execute(
            """
            select
                chunks.id as chunk_id,
                chunks.document_id,
                chunks.page_number,
                chunks.text,
                papers.title as paper_title
            from chunks
            join papers on papers.id = chunks.paper_id
            where chunks.paper_id = ?
            order by chunks.document_id, chunks.page_number, chunks.chunk_index
            """,
            (paper_id,),
        ).fetchall()
        for row in rows:
            self._conn.execute(
                "delete from chunks_fts where rowid = ?",
                (row["chunk_id"],),
            )
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
                    row["chunk_id"],
                    row["text"],
                    row["paper_title"],
                    paper_id,
                    row["document_id"],
                    row["chunk_id"],
                    row["page_number"],
                ),
            )


class SearchResultsRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def replace_for_query(
        self,
        query: str,
        candidates: list[DiscoveryCandidate],
    ) -> list[SearchResultRecord]:
        self._conn.execute("delete from search_results where query = ?", (query,))
        for candidate in candidates:
            self._conn.execute(
                """
                insert into search_results (
                    query,
                    source,
                    external_id,
                    title,
                    authors,
                    year,
                    doi,
                    venue,
                    abstract,
                    arxiv_id,
                    pdf_url,
                    landing_url
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(source, external_id) do update set
                    query = excluded.query,
                    title = excluded.title,
                    authors = excluded.authors,
                    year = excluded.year,
                    doi = excluded.doi,
                    venue = excluded.venue,
                    abstract = excluded.abstract,
                    arxiv_id = excluded.arxiv_id,
                    pdf_url = excluded.pdf_url,
                    landing_url = excluded.landing_url
                """,
                (
                    query,
                    candidate.source,
                    candidate.external_id,
                    candidate.title,
                    candidate.authors,
                    candidate.year,
                    _normalize_doi(candidate.doi),
                    candidate.venue,
                    candidate.abstract,
                    candidate.arxiv_id,
                    candidate.pdf_url,
                    candidate.landing_url,
                ),
            )
        return self.list_for_query(query)

    def list_for_query(self, query: str) -> list[SearchResultRecord]:
        rows = self._conn.execute(
            """
            select
                id,
                query,
                source,
                external_id,
                title,
                authors,
                year,
                doi,
                venue,
                abstract,
                arxiv_id,
                pdf_url,
                landing_url,
                created_at
            from search_results
            where query = ?
            order by id
            """,
            (query,),
        ).fetchall()
        return [SearchResultRecord(**dict(row)) for row in rows]

    def get(self, result_id: int) -> SearchResultRecord:
        row = self._conn.execute(
            """
            select
                id,
                query,
                source,
                external_id,
                title,
                authors,
                year,
                doi,
                venue,
                abstract,
                arxiv_id,
                pdf_url,
                landing_url,
                created_at
            from search_results
            where id = ?
            """,
            (result_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"search result not found: {result_id}")
        return SearchResultRecord(**dict(row))


class NotesRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        paper_id: int,
        body: str,
        page_number: int | None,
        source_span: str | None,
        selected_text: str | None,
        note_type: str,
        qna_id: int | None,
    ) -> Note:
        cursor = self._conn.execute(
            """
            insert into notes (
                paper_id,
                body,
                page_number,
                source_span,
                selected_text,
                note_type,
                qna_id
            )
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper_id,
                body,
                page_number,
                source_span,
                selected_text,
                note_type,
                qna_id,
            ),
        )
        return self.get(cursor.lastrowid)

    def get(self, note_id: int) -> Note:
        row = self._conn.execute(
            """
            select
                id,
                paper_id,
                body,
                page_number,
                source_span,
                selected_text,
                note_type,
                qna_id,
                created_at,
                updated_at
            from notes
            where id = ?
            """,
            (note_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"note not found: {note_id}")
        return Note(**dict(row))

    def list_for_paper(self, paper_id: int) -> list[Note]:
        rows = self._conn.execute(
            """
            select
                id,
                paper_id,
                body,
                page_number,
                source_span,
                selected_text,
                note_type,
                qna_id,
                created_at,
                updated_at
            from notes
            where paper_id = ?
            order by created_at desc, id desc
            """,
            (paper_id,),
        ).fetchall()
        return [Note(**dict(row)) for row in rows]


class HighlightsRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        paper_id: int,
        page_number: int,
        source_span: str,
        selected_text: str,
        color: str,
        note_id: int | None,
    ) -> Highlight:
        cursor = self._conn.execute(
            """
            insert into highlights (
                paper_id,
                page_number,
                source_span,
                selected_text,
                color,
                note_id
            )
            values (?, ?, ?, ?, ?, ?)
            """,
            (
                paper_id,
                page_number,
                source_span,
                selected_text,
                color,
                note_id,
            ),
        )
        return self.get(cursor.lastrowid)

    def get(self, highlight_id: int) -> Highlight:
        row = self._conn.execute(
            """
            select
                id,
                paper_id,
                page_number,
                source_span,
                selected_text,
                color,
                note_id,
                created_at
            from highlights
            where id = ?
            """,
            (highlight_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"highlight not found: {highlight_id}")
        return Highlight(**dict(row))

    def list_for_paper(self, paper_id: int) -> list[Highlight]:
        rows = self._conn.execute(
            """
            select
                id,
                paper_id,
                page_number,
                source_span,
                selected_text,
                color,
                note_id,
                created_at
            from highlights
            where paper_id = ?
            order by page_number asc, id asc
            """,
            (paper_id,),
        ).fetchall()
        return [Highlight(**dict(row)) for row in rows]


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

    def relevant_for_paper(
        self,
        paper_id: int,
        query: str,
        limit: int = 4,
    ) -> list[Chunk]:
        chunks = self.list_for_paper(paper_id)
        if not chunks:
            return []

        query_terms = _tokenize(query)
        if not query_terms:
            return chunks[:limit]

        scored_chunks = [
            (_overlap_score(query_terms, _tokenize(chunk.text)), index, chunk)
            for index, chunk in enumerate(chunks)
        ]
        scored_chunks.sort(key=lambda item: (-item[0], item[1]))
        if scored_chunks[0][0] == 0:
            return chunks[:limit]
        return [
            chunk
            for score, _, chunk in scored_chunks
            if score > 0
        ][:limit]

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


class SettingsRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_provider_settings(self) -> ProviderSettings:
        row = self._conn.execute(
            "select value from settings where key = ?",
            (PROVIDER_SETTINGS_KEY,),
        ).fetchone()
        if row is None:
            return ProviderSettings()
        payload = json.loads(str(row["value"]))
        return ProviderSettings(
            provider=payload.get("provider", "none"),
            base_url=payload.get("base_url"),
            model=payload.get("model"),
            api_key=payload.get("api_key"),
            outbound_context_policy=payload.get(
                "outbound_context_policy",
                "snippets_only",
            ),
            proxy_url=payload.get("proxy_url"),
        )

    def save_provider_settings(self, settings: ProviderSettings) -> ProviderSettings:
        payload = json.dumps(
            {
                "provider": settings.provider,
                "base_url": settings.base_url,
                "model": settings.model,
                "api_key": settings.api_key,
                "outbound_context_policy": settings.outbound_context_policy,
                "proxy_url": settings.proxy_url,
            },
            ensure_ascii=True,
        )
        self._conn.execute(
            """
            insert into settings (key, value, updated_at)
            values (?, ?, current_timestamp)
            on conflict(key) do update set
                value = excluded.value,
                updated_at = current_timestamp
            """,
            (PROVIDER_SETTINGS_KEY, payload),
        )
        return self.get_provider_settings()


class QnaRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        paper_id: int,
        question: str,
        answer: str,
        cited_chunks: list[dict[str, object]],
        mode: str,
        provider: str,
    ) -> QnaEntry:
        cursor = self._conn.execute(
            """
            insert into qna_entries (
                paper_id,
                question,
                answer,
                cited_chunks,
                mode,
                provider
            )
            values (?, ?, ?, ?, ?, ?)
            """,
            (
                paper_id,
                question,
                answer,
                json.dumps(cited_chunks, ensure_ascii=True),
                mode,
                provider,
            ),
        )
        return self.get(cursor.lastrowid)

    def get(self, entry_id: int) -> QnaEntry:
        row = self._conn.execute(
            """
            select id, paper_id, question, answer, cited_chunks, mode, provider, created_at
            from qna_entries
            where id = ?
            """,
            (entry_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"qna entry not found: {entry_id}")
        return _qna_from_row(row)

    def list_for_paper(self, paper_id: int) -> list[QnaEntry]:
        rows = self._conn.execute(
            """
            select id, paper_id, question, answer, cited_chunks, mode, provider, created_at
            from qna_entries
            where paper_id = ?
            order by created_at desc, id desc
            """,
            (paper_id,),
        ).fetchall()
        return [_qna_from_row(row) for row in rows]


def _qna_from_row(row: sqlite3.Row) -> QnaEntry:
    payload = dict(row)
    payload["cited_chunks"] = json.loads(str(payload["cited_chunks"]))
    return QnaEntry(**payload)


def _tokenize(value: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", value.lower()))


def _overlap_score(query_terms: set[str], chunk_terms: set[str]) -> int:
    return len(query_terms & chunk_terms)


def _normalize_doi(doi: str | None) -> str | None:
    if doi is None:
        return None
    normalized = doi.strip().lower()
    return normalized or None


def _normalize_tag_name(tag_name: str | None) -> str | None:
    if tag_name is None:
        return None
    normalized = " ".join(tag_name.strip().split())
    return normalized or None
