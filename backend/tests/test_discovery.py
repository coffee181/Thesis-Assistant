import httpx

from knowledge_agent.discovery import (
    ExternalDiscoveryClient,
    classify_query,
    merge_candidates,
    normalize_arxiv_feed,
    normalize_crossref_work,
    normalize_openalex_work,
    normalize_semantic_scholar_paper,
    normalize_unpaywall_record,
)
from knowledge_agent.models import DiscoveryCandidate


def test_classify_query_detects_doi_arxiv_and_keyword():
    assert classify_query("https://doi.org/10.1234/ABC.Def") == (
        "doi",
        "10.1234/ABC.Def",
    )
    assert classify_query("https://arxiv.org/abs/2401.12345v2") == (
        "arxiv",
        "2401.12345",
    )
    assert classify_query("local retrieval agents") == (
        "keyword",
        "local retrieval agents",
    )


def test_normalize_openalex_work_extracts_metadata_and_pdf_url():
    candidate = normalize_openalex_work(
        {
            "id": "https://openalex.org/W123",
            "doi": "https://doi.org/10.1234/local",
            "title": "Local Knowledge Agents",
            "publication_year": 2024,
            "authorships": [
                {"author": {"display_name": "Jane Doe"}},
                {"author": {"display_name": "John Smith"}},
            ],
            "primary_location": {
                "landing_page_url": "https://example.test/local",
                "pdf_url": "https://example.test/local.pdf",
                "source": {"display_name": "Journal of Local Research"},
            },
            "abstract_inverted_index": {
                "Traceable": [0],
                "assistants": [1],
                "work.": [2],
            },
        }
    )

    assert candidate.source == "openalex"
    assert candidate.external_id == "W123"
    assert candidate.title == "Local Knowledge Agents"
    assert candidate.authors == "Jane Doe and John Smith"
    assert candidate.year == 2024
    assert candidate.doi == "10.1234/local"
    assert candidate.venue == "Journal of Local Research"
    assert candidate.abstract == "Traceable assistants work."
    assert candidate.pdf_url == "https://example.test/local.pdf"
    assert candidate.landing_url == "https://example.test/local"


def test_normalize_arxiv_feed_extracts_entries():
    candidates = normalize_arxiv_feed(
        """
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/2401.12345v2</id>
            <title>Local Knowledge Agents</title>
            <summary>Traceable local assistants.</summary>
            <published>2024-01-15T00:00:00Z</published>
            <author><name>Jane Doe</name></author>
            <author><name>John Smith</name></author>
            <link href="http://arxiv.org/abs/2401.12345v2" rel="alternate" type="text/html" />
            <link href="http://arxiv.org/pdf/2401.12345v2" rel="related" type="application/pdf" />
          </entry>
        </feed>
        """
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.source == "arxiv"
    assert candidate.external_id == "2401.12345"
    assert candidate.title == "Local Knowledge Agents"
    assert candidate.authors == "Jane Doe and John Smith"
    assert candidate.year == 2024
    assert candidate.venue == "arXiv"
    assert candidate.abstract == "Traceable local assistants."
    assert candidate.arxiv_id == "2401.12345"
    assert candidate.pdf_url == "http://arxiv.org/pdf/2401.12345v2"
    assert candidate.landing_url == "http://arxiv.org/abs/2401.12345v2"


def test_normalize_unpaywall_record_extracts_best_oa_location():
    candidate = normalize_unpaywall_record(
        {
            "doi": "10.1234/local",
            "title": "Local Knowledge Agents",
            "published_date": "2024-05-01",
            "journal_name": "Journal of Local Research",
            "z_authors": [
                {"given": "Jane", "family": "Doe"},
                {"given": "John", "family": "Smith"},
            ],
            "best_oa_location": {
                "url_for_pdf": "https://example.test/local.pdf",
                "url": "https://example.test/local",
            },
        }
    )

    assert candidate.source == "unpaywall"
    assert candidate.external_id == "10.1234/local"
    assert candidate.title == "Local Knowledge Agents"
    assert candidate.authors == "Jane Doe and John Smith"
    assert candidate.year == 2024
    assert candidate.doi == "10.1234/local"
    assert candidate.venue == "Journal of Local Research"
    assert candidate.pdf_url == "https://example.test/local.pdf"
    assert candidate.landing_url == "https://example.test/local"


def test_normalize_crossref_work_extracts_metadata_and_links():
    candidate = normalize_crossref_work(
        {
            "DOI": "10.1234/CROSS",
            "title": ["Crossref Local Agents"],
            "author": [
                {"given": "Jane", "family": "Doe"},
                {"name": "Local Consortium"},
            ],
            "published-print": {"date-parts": [[2023, 5, 1]]},
            "container-title": ["Proceedings of Local Research"],
            "abstract": "<jats:p>Traceable discovery from Crossref.</jats:p>",
            "link": [
                {
                    "URL": "https://example.test/crossref.pdf",
                    "content-type": "application/pdf",
                }
            ],
            "URL": "https://doi.org/10.1234/CROSS",
        }
    )

    assert candidate.source == "crossref"
    assert candidate.external_id == "10.1234/cross"
    assert candidate.title == "Crossref Local Agents"
    assert candidate.authors == "Jane Doe and Local Consortium"
    assert candidate.year == 2023
    assert candidate.doi == "10.1234/cross"
    assert candidate.venue == "Proceedings of Local Research"
    assert candidate.abstract == "Traceable discovery from Crossref."
    assert candidate.pdf_url == "https://example.test/crossref.pdf"
    assert candidate.landing_url == "https://doi.org/10.1234/CROSS"


def test_normalize_semantic_scholar_paper_extracts_open_access_pdf():
    candidate = normalize_semantic_scholar_paper(
        {
            "paperId": "S2-123",
            "title": "Semantic Scholar Local Agents",
            "authors": [{"name": "Jane Doe"}, {"name": "John Smith"}],
            "year": 2024,
            "venue": "Local AI",
            "abstract": "Semantic Scholar discovery.",
            "externalIds": {"DOI": "10.1234/semantic", "ArXiv": "2401.12345"},
            "openAccessPdf": {"url": "https://example.test/semantic.pdf"},
            "url": "https://www.semanticscholar.org/paper/S2-123",
        }
    )

    assert candidate.source == "semantic_scholar"
    assert candidate.external_id == "S2-123"
    assert candidate.title == "Semantic Scholar Local Agents"
    assert candidate.authors == "Jane Doe and John Smith"
    assert candidate.year == 2024
    assert candidate.doi == "10.1234/semantic"
    assert candidate.arxiv_id == "2401.12345"
    assert candidate.pdf_url == "https://example.test/semantic.pdf"


def test_merge_candidates_deduplicates_by_doi_and_keeps_pdf_url():
    merged = merge_candidates(
        [
            DiscoveryCandidate(
                source="openalex",
                external_id="W123",
                title="Local Knowledge Agents",
                authors="Jane Doe",
                year=2024,
                doi="10.1234/local",
                venue="Journal of Local Research",
                abstract=None,
                arxiv_id=None,
                pdf_url=None,
                landing_url="https://example.test/local",
            ),
            DiscoveryCandidate(
                source="unpaywall",
                external_id="10.1234/local",
                title="Local Knowledge Agents",
                authors=None,
                year=2024,
                doi="10.1234/local",
                venue=None,
                abstract="Traceable assistants.",
                arxiv_id=None,
                pdf_url="https://example.test/local.pdf",
                landing_url=None,
            ),
        ]
    )

    assert len(merged) == 1
    assert merged[0].source == "openalex"
    assert merged[0].authors == "Jane Doe"
    assert merged[0].abstract == "Traceable assistants."
    assert merged[0].pdf_url == "https://example.test/local.pdf"


def test_external_discovery_client_uses_injected_http_client_for_doi_search():
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if "openalex.org" in request.url.host:
            return httpx.Response(
                200,
                json={
                    "id": "https://openalex.org/W123",
                    "doi": "https://doi.org/10.1234/local",
                    "title": "Local Knowledge Agents",
                    "publication_year": 2024,
                    "authorships": [],
                    "primary_location": {"landing_page_url": "https://example.test/local"},
                },
            )
        return httpx.Response(
            200,
            json={
                "doi": "10.1234/local",
                "title": "Local Knowledge Agents",
                "best_oa_location": {
                    "url_for_pdf": "https://example.test/local.pdf",
                    "url": "https://example.test/local",
                },
            },
        )

    client = ExternalDiscoveryClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    candidates = client.search("10.1234/local")

    assert len(candidates) == 1
    assert candidates[0].doi == "10.1234/local"
    assert candidates[0].pdf_url == "https://example.test/local.pdf"
    assert any("openalex.org/works/doi:10.1234%2Flocal" in url for url in requested_urls)
    assert any("api.unpaywall.org/v2/10.1234%2Flocal" in url for url in requested_urls)


def test_external_discovery_client_queries_crossref_and_semantic_scholar():
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        host = request.url.host or ""
        if "openalex.org" in host:
            return httpx.Response(200, json={"results": []})
        if "arxiv.org" in host:
            return httpx.Response(
                200,
                text='<feed xmlns="http://www.w3.org/2005/Atom"></feed>',
            )
        if "crossref.org" in host:
            return httpx.Response(
                200,
                json={
                    "message": {
                        "items": [
                            {
                                "DOI": "10.1234/cross",
                                "title": ["Crossref Local Agents"],
                                "URL": "https://doi.org/10.1234/cross",
                            }
                        ]
                    }
                },
            )
        if "semanticscholar.org" in host:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "paperId": "S2-123",
                            "title": "Semantic Scholar Local Agents",
                            "externalIds": {"DOI": "10.1234/semantic"},
                        }
                    ]
                },
            )
        return httpx.Response(404)

    client = ExternalDiscoveryClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )

    candidates = client.search("local agents", limit=5)

    assert [candidate.source for candidate in candidates] == [
        "crossref",
        "semantic_scholar",
    ]
    assert any("api.crossref.org/works" in url for url in requested_urls)
    assert any(
        "api.semanticscholar.org/graph/v1/paper/search" in url
        for url in requested_urls
    )
