import re
import xml.etree.ElementTree as ET
from dataclasses import replace
from urllib.parse import quote

import httpx

from knowledge_agent.models import DiscoveryCandidate


OPENALEX_BASE_URL = "https://api.openalex.org"
CROSSREF_BASE_URL = "https://api.crossref.org"
ARXIV_BASE_URL = "https://export.arxiv.org/api/query"
SEMANTIC_SCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1"
SEMANTIC_SCHOLAR_FIELDS = (
    "paperId,title,authors,year,venue,abstract,externalIds,openAccessPdf,url"
)
UNPAYWALL_BASE_URL = "https://api.unpaywall.org/v2"
UNPAYWALL_EMAIL = "knowledge-agent@example.invalid"


def classify_query(query: str) -> tuple[str, str]:
    cleaned = query.strip()
    doi_match = re.search(r"10\.\d{4,9}/[^\s]+", cleaned, re.IGNORECASE)
    if doi_match:
        return "doi", doi_match.group(0).rstrip(".,;")

    arxiv_match = re.search(
        r"(?:arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5})(?:v\d+)?",
        cleaned,
        re.IGNORECASE,
    )
    if arxiv_match:
        return "arxiv", arxiv_match.group(1)

    return "keyword", cleaned


def normalize_openalex_work(work: dict[str, object]) -> DiscoveryCandidate:
    primary_location = _dict_value(work.get("primary_location"))
    source = _dict_value(primary_location.get("source"))
    return DiscoveryCandidate(
        source="openalex",
        external_id=_openalex_id(str(work.get("id") or work.get("doi") or "")),
        title=_clean_text(_string_value(work.get("title"))) or "Untitled",
        authors=_authors_from_openalex(work.get("authorships")),
        year=_int_value(work.get("publication_year")),
        doi=_normalize_doi(_string_value(work.get("doi"))),
        venue=_clean_text(_string_value(source.get("display_name"))),
        abstract=_abstract_from_openalex(work.get("abstract_inverted_index")),
        arxiv_id=None,
        pdf_url=_clean_text(_string_value(primary_location.get("pdf_url"))),
        landing_url=_clean_text(_string_value(primary_location.get("landing_page_url"))),
    )


def normalize_arxiv_feed(content: str) -> list[DiscoveryCandidate]:
    root = ET.fromstring(content)
    candidates: list[DiscoveryCandidate] = []
    for entry in _children(root, "entry"):
        entry_id = _child_text(entry, "id") or ""
        arxiv_id = _strip_arxiv_version(_last_path_part(entry_id))
        candidates.append(
            DiscoveryCandidate(
                source="arxiv",
                external_id=arxiv_id or entry_id,
                title=_clean_text(_child_text(entry, "title")) or "Untitled",
                authors=_authors_from_arxiv(entry),
                year=_year_from_text(_child_text(entry, "published")),
                doi=None,
                venue="arXiv",
                abstract=_clean_text(_child_text(entry, "summary")),
                arxiv_id=arxiv_id or None,
                pdf_url=_arxiv_link(entry, "application/pdf"),
                landing_url=_arxiv_link(entry, "text/html") or _clean_text(entry_id),
            )
        )
    return candidates


def normalize_crossref_work(work: dict[str, object]) -> DiscoveryCandidate:
    doi = _normalize_doi(_string_value(work.get("DOI")))
    return DiscoveryCandidate(
        source="crossref",
        external_id=doi or _clean_text(_string_value(work.get("URL"))) or "unknown",
        title=_clean_text(_first_string(work.get("title"))) or "Untitled",
        authors=_authors_from_crossref(work.get("author")),
        year=_year_from_crossref(work),
        doi=doi,
        venue=_clean_text(_first_string(work.get("container-title"))),
        abstract=_strip_markup(_clean_text(_string_value(work.get("abstract")))),
        arxiv_id=None,
        pdf_url=_crossref_pdf_url(work.get("link")),
        landing_url=_clean_text(_string_value(work.get("URL"))),
    )


def normalize_semantic_scholar_paper(paper: dict[str, object]) -> DiscoveryCandidate:
    external_ids = _dict_value(paper.get("externalIds"))
    arxiv_id = _strip_arxiv_version(_string_value(external_ids.get("ArXiv")) or "")
    return DiscoveryCandidate(
        source="semantic_scholar",
        external_id=_clean_text(_string_value(paper.get("paperId"))) or "unknown",
        title=_clean_text(_string_value(paper.get("title"))) or "Untitled",
        authors=_authors_from_semantic_scholar(paper.get("authors")),
        year=_int_value(paper.get("year")),
        doi=_normalize_doi(_string_value(external_ids.get("DOI"))),
        venue=_clean_text(_string_value(paper.get("venue"))),
        abstract=_clean_text(_string_value(paper.get("abstract"))),
        arxiv_id=arxiv_id or None,
        pdf_url=_clean_text(
            _string_value(_dict_value(paper.get("openAccessPdf")).get("url"))
        ),
        landing_url=_clean_text(_string_value(paper.get("url"))),
    )


def normalize_unpaywall_record(record: dict[str, object]) -> DiscoveryCandidate:
    best_location = _dict_value(record.get("best_oa_location"))
    doi = _normalize_doi(_string_value(record.get("doi")))
    return DiscoveryCandidate(
        source="unpaywall",
        external_id=doi or _clean_text(_string_value(record.get("doi"))) or "unknown",
        title=_clean_text(_string_value(record.get("title"))) or "Untitled",
        authors=_authors_from_unpaywall(record.get("z_authors")),
        year=_year_from_text(_string_value(record.get("published_date"))),
        doi=doi,
        venue=_clean_text(_string_value(record.get("journal_name"))),
        abstract=None,
        arxiv_id=None,
        pdf_url=_clean_text(_string_value(best_location.get("url_for_pdf"))),
        landing_url=_clean_text(_string_value(best_location.get("url"))),
    )


def merge_candidates(candidates: list[DiscoveryCandidate]) -> list[DiscoveryCandidate]:
    merged: list[DiscoveryCandidate] = []
    positions: dict[str, int] = {}
    for candidate in candidates:
        key = _candidate_key(candidate)
        if key not in positions:
            positions[key] = len(merged)
            merged.append(candidate)
            continue
        current = merged[positions[key]]
        merged[positions[key]] = replace(
            current,
            title=current.title or candidate.title,
            authors=current.authors or candidate.authors,
            year=current.year if current.year is not None else candidate.year,
            doi=current.doi or candidate.doi,
            venue=current.venue or candidate.venue,
            abstract=current.abstract or candidate.abstract,
            arxiv_id=current.arxiv_id or candidate.arxiv_id,
            pdf_url=current.pdf_url or candidate.pdf_url,
            landing_url=current.landing_url or candidate.landing_url,
        )
    return merged


class ExternalDiscoveryClient:
    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self._http_client = http_client or httpx.Client(timeout=15.0)

    def search(self, query: str, limit: int = 10) -> list[DiscoveryCandidate]:
        query_type, normalized_query = classify_query(query)
        candidates: list[DiscoveryCandidate] = []
        candidates.extend(self._search_openalex(query_type, normalized_query, limit))
        if query_type != "doi":
            candidates.extend(self._search_arxiv(normalized_query, limit))
        candidates.extend(self._search_crossref(query_type, normalized_query, limit))
        candidates.extend(
            self._search_semantic_scholar(query_type, normalized_query, limit)
        )
        if query_type == "doi":
            candidates.extend(self._search_unpaywall(normalized_query))
        return merge_candidates(candidates)[:limit]

    def _search_openalex(
        self,
        query_type: str,
        query: str,
        limit: int,
    ) -> list[DiscoveryCandidate]:
        try:
            if query_type == "doi":
                response = self._http_client.get(
                    f"{OPENALEX_BASE_URL}/works/doi:{quote(query, safe='')}"
                )
                response.raise_for_status()
                return [normalize_openalex_work(response.json())]

            response = self._http_client.get(
                f"{OPENALEX_BASE_URL}/works",
                params={"search": query, "per-page": str(limit)},
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results", []) if isinstance(payload, dict) else []
            return [
                normalize_openalex_work(work)
                for work in results
                if isinstance(work, dict)
            ]
        except Exception:
            return []

    def _search_arxiv(self, query: str, limit: int) -> list[DiscoveryCandidate]:
        try:
            response = self._http_client.get(
                ARXIV_BASE_URL,
                params={"search_query": f"all:{query}", "max_results": str(limit)},
            )
            response.raise_for_status()
            return normalize_arxiv_feed(response.text)
        except Exception:
            return []

    def _search_crossref(
        self,
        query_type: str,
        query: str,
        limit: int,
    ) -> list[DiscoveryCandidate]:
        try:
            if query_type == "doi":
                response = self._http_client.get(
                    f"{CROSSREF_BASE_URL}/works/{quote(query, safe='')}"
                )
                response.raise_for_status()
                message = _dict_value(response.json().get("message"))
                return [normalize_crossref_work(message)] if message else []

            response = self._http_client.get(
                f"{CROSSREF_BASE_URL}/works",
                params={"query.bibliographic": query, "rows": str(limit)},
            )
            response.raise_for_status()
            message = _dict_value(response.json().get("message"))
            items = message.get("items")
            if not isinstance(items, list):
                return []
            return [
                normalize_crossref_work(item)
                for item in items
                if isinstance(item, dict)
            ]
        except Exception:
            return []

    def _search_semantic_scholar(
        self,
        query_type: str,
        query: str,
        limit: int,
    ) -> list[DiscoveryCandidate]:
        try:
            if query_type in {"doi", "arxiv"}:
                identifier_type = "DOI" if query_type == "doi" else "ARXIV"
                response = self._http_client.get(
                    (
                        f"{SEMANTIC_SCHOLAR_BASE_URL}/paper/"
                        f"{identifier_type}:{quote(query, safe='')}"
                    ),
                    params={"fields": SEMANTIC_SCHOLAR_FIELDS},
                )
                response.raise_for_status()
                return _semantic_scholar_candidates_from_payload(response.json())

            response = self._http_client.get(
                f"{SEMANTIC_SCHOLAR_BASE_URL}/paper/search",
                params={
                    "query": query,
                    "limit": str(limit),
                    "fields": SEMANTIC_SCHOLAR_FIELDS,
                },
            )
            response.raise_for_status()
            return _semantic_scholar_candidates_from_payload(response.json())
        except Exception:
            return []

    def _search_unpaywall(self, doi: str) -> list[DiscoveryCandidate]:
        try:
            response = self._http_client.get(
                f"{UNPAYWALL_BASE_URL}/{quote(doi, safe='')}",
                params={"email": UNPAYWALL_EMAIL},
            )
            response.raise_for_status()
            return [normalize_unpaywall_record(response.json())]
        except Exception:
            return []


def _candidate_key(candidate: DiscoveryCandidate) -> str:
    doi = _normalize_doi(candidate.doi)
    if doi:
        return f"doi:{doi}"
    if candidate.arxiv_id:
        return f"arxiv:{candidate.arxiv_id}"
    return f"{candidate.source}:{candidate.external_id}"


def _openalex_id(value: str) -> str:
    cleaned = value.rstrip("/")
    return cleaned.rsplit("/", 1)[-1] if cleaned else "unknown"


def _authors_from_openalex(value: object) -> str | None:
    authors = []
    if isinstance(value, list):
        for authorship in value:
            author = _dict_value(_dict_value(authorship).get("author"))
            name = _clean_text(_string_value(author.get("display_name")))
            if name:
                authors.append(name)
    return " and ".join(authors) or None


def _authors_from_arxiv(entry: ET.Element) -> str | None:
    authors = [
        _clean_text(_child_text(author, "name"))
        for author in _children(entry, "author")
    ]
    return " and ".join(author for author in authors if author) or None


def _authors_from_crossref(value: object) -> str | None:
    authors = []
    if isinstance(value, list):
        for item in value:
            author = _dict_value(item)
            literal_name = _clean_text(_string_value(author.get("name")))
            given = _clean_text(_string_value(author.get("given")))
            family = _clean_text(_string_value(author.get("family")))
            name = literal_name or " ".join(part for part in [given, family] if part)
            if name:
                authors.append(name)
    return " and ".join(authors) or None


def _authors_from_semantic_scholar(value: object) -> str | None:
    authors = []
    if isinstance(value, list):
        for item in value:
            name = _clean_text(_string_value(_dict_value(item).get("name")))
            if name:
                authors.append(name)
    return " and ".join(authors) or None


def _authors_from_unpaywall(value: object) -> str | None:
    authors = []
    if isinstance(value, list):
        for item in value:
            author = _dict_value(item)
            given = _clean_text(_string_value(author.get("given")))
            family = _clean_text(_string_value(author.get("family")))
            name = " ".join(part for part in [given, family] if part)
            if name:
                authors.append(name)
    return " and ".join(authors) or None


def _year_from_crossref(work: dict[str, object]) -> int | None:
    for key in (
        "published-print",
        "published-online",
        "published",
        "issued",
        "created",
    ):
        year = _year_from_date_parts(_dict_value(work.get(key)).get("date-parts"))
        if year is not None:
            return year
    return None


def _year_from_date_parts(value: object) -> int | None:
    if not isinstance(value, list) or not value:
        return None
    first_date = value[0]
    if not isinstance(first_date, list) or not first_date:
        return None
    year = first_date[0]
    return year if isinstance(year, int) else None


def _abstract_from_openalex(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    positioned: dict[int, str] = {}
    for word, positions in value.items():
        if not isinstance(word, str) or not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int):
                positioned[position] = word
    if not positioned:
        return None
    return " ".join(positioned[index] for index in sorted(positioned))


def _crossref_pdf_url(value: object) -> str | None:
    if not isinstance(value, list):
        return None
    for item in value:
        link = _dict_value(item)
        url = _clean_text(_string_value(link.get("URL")))
        if not url:
            continue
        content_type = (_clean_text(_string_value(link.get("content-type"))) or "").lower()
        if "pdf" in content_type or url.lower().endswith(".pdf"):
            return url
    return None


def _arxiv_link(entry: ET.Element, content_type: str) -> str | None:
    for link in _children(entry, "link"):
        if link.attrib.get("type") == content_type:
            return _clean_text(link.attrib.get("href"))
    return None


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(element) if _local_name(child.tag) == name]


def _child_text(element: ET.Element, name: str) -> str | None:
    for child in _children(element, name):
        return child.text
    return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _last_path_part(value: str) -> str:
    cleaned = value.rstrip("/")
    return cleaned.rsplit("/", 1)[-1]


def _strip_arxiv_version(value: str) -> str:
    return re.sub(r"v\d+$", "", value)


def _semantic_scholar_candidates_from_payload(
    payload: object,
) -> list[DiscoveryCandidate]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if isinstance(data, list):
        return [
            normalize_semantic_scholar_paper(item)
            for item in data
            if _has_semantic_scholar_identity(item)
        ]
    if _has_semantic_scholar_identity(payload):
        return [normalize_semantic_scholar_paper(payload)]
    return []


def _has_semantic_scholar_identity(value: object) -> bool:
    paper = _dict_value(value)
    return bool(paper.get("paperId") or paper.get("externalIds"))


def _first_string(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                return item
    return None


def _strip_markup(value: str | None) -> str | None:
    if value is None:
        return None
    return _clean_text(re.sub(r"<[^>]+>", "", value))


def _year_from_text(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\d{4}", value)
    return int(match.group(0)) if match else None


def _int_value(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _dict_value(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _string_value(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def _normalize_doi(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    cleaned = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", cleaned, flags=re.IGNORECASE)
    return cleaned.lower() or None
