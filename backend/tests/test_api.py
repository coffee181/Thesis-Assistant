from pathlib import Path

from fastapi.testclient import TestClient

from knowledge_agent.main import create_app
from knowledge_agent.models import DiscoveryCandidate, ProviderSettings
from knowledge_agent.providers import ProviderMessage


class ApiRecordingChatProvider:
    def __init__(self, answer: str = "该论文使用检索增强生成。"):
        self.answer = answer
        self.calls: list[dict[str, object]] = []

    def complete(
        self,
        settings: ProviderSettings,
        messages: list[ProviderMessage],
    ) -> str:
        self.calls.append({"settings": settings, "messages": messages})
        return self.answer


class FakeDiscoveryClient:
    def __init__(self, candidates: list[DiscoveryCandidate]):
        self.candidates = candidates
        self.queries: list[str] = []

    def search(self, query: str, limit: int = 10) -> list[DiscoveryCandidate]:
        self.queries.append(query)
        return self.candidates[:limit]


def test_import_pdf_endpoint_then_list_papers(tmp_path: Path):
    source = tmp_path / "Endpoint Paper.pdf"
    source.write_bytes(b"%PDF-1.4 endpoint pdf")
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))

    import_response = client.post(
        "/api/imports/pdf",
        json={"source_path": str(source)},
    )
    list_response = client.get("/api/papers")

    assert import_response.status_code == 201
    assert import_response.json()["imported"] is True
    assert import_response.json()["paper"]["title"] == "Endpoint Paper"
    assert list_response.status_code == 200
    assert list_response.json()["papers"][0]["title"] == "Endpoint Paper"


def test_import_pdf_endpoint_reports_missing_file(tmp_path: Path):
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))

    response = client.post(
        "/api/imports/pdf",
        json={"source_path": str(tmp_path / "missing.pdf")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "source PDF not found"


def test_import_bibliography_endpoint_imports_bib_file_and_lists_metadata(
    tmp_path: Path,
):
    source = tmp_path / "library.bib"
    source.write_text(
        """
        @article{doe2024local,
          title = {Local Knowledge Agents},
          author = {Jane Doe and John Smith},
          year = {2024},
          doi = {10.1234/local},
          journal = {Journal of Local Research},
          abstract = {Traceable local research assistants.}
        }
        """,
        encoding="utf-8",
    )
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))

    import_response = client.post(
        "/api/imports/bibliography",
        json={"source_path": str(source)},
    )
    list_response = client.get("/api/papers")

    assert import_response.status_code == 201
    assert import_response.json()["format"] == "bibtex"
    assert import_response.json()["imported_count"] == 1
    assert import_response.json()["updated_count"] == 0
    paper = list_response.json()["papers"][0]
    assert paper["title"] == "Local Knowledge Agents"
    assert paper["authors"] == "Jane Doe and John Smith"
    assert paper["year"] == 2024
    assert paper["doi"] == "10.1234/local"
    assert paper["venue"] == "Journal of Local Research"
    assert paper["citation_key"] == "doe2024local"
    assert paper["entry_type"] == "article"


def test_import_bibliography_endpoint_reimport_updates_existing_doi(
    tmp_path: Path,
):
    source = tmp_path / "library.bib"
    source.write_text(
        """
        @article{doe2024local,
          title = {Local Knowledge Agents},
          author = {Jane Doe},
          year = {2024},
          doi = {10.1234/local},
          journal = {Original Venue}
        }
        """,
        encoding="utf-8",
    )
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))
    client.post("/api/imports/bibliography", json={"source_path": str(source)})
    source.write_text(
        """
        @article{doe2025local,
          title = {Updated Local Knowledge Agents},
          author = {Jane Doe and John Smith},
          year = {2025},
          doi = {10.1234/local},
          journal = {Updated Venue}
        }
        """,
        encoding="utf-8",
    )

    response = client.post(
        "/api/imports/bibliography",
        json={"source_path": str(source)},
    )
    list_response = client.get("/api/papers")

    assert response.status_code == 201
    assert response.json()["imported_count"] == 0
    assert response.json()["updated_count"] == 1
    papers = list_response.json()["papers"]
    assert len(papers) == 1
    assert papers[0]["title"] == "Updated Local Knowledge Agents"
    assert papers[0]["authors"] == "Jane Doe and John Smith"
    assert papers[0]["year"] == 2025
    assert papers[0]["venue"] == "Updated Venue"


def test_export_bibliography_endpoint_returns_bibtex_and_ris(tmp_path: Path):
    source = tmp_path / "library.bib"
    source.write_text(
        """
        @article{doe2024local,
          title = {Local Knowledge Agents},
          author = {Jane Doe and John Smith},
          year = {2024},
          doi = {10.1234/local},
          journal = {Journal of Local Research}
        }
        """,
        encoding="utf-8",
    )
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))
    client.post("/api/imports/bibliography", json={"source_path": str(source)})

    bibtex_response = client.get(
        "/api/exports/bibliography",
        params={"format": "bibtex"},
    )
    ris_response = client.get(
        "/api/exports/bibliography",
        params={"format": "ris"},
    )

    assert bibtex_response.status_code == 200
    assert bibtex_response.json()["format"] == "bibtex"
    assert "@article{doe2024local," in bibtex_response.json()["content"]
    assert ris_response.status_code == 200
    assert ris_response.json()["format"] == "ris"
    assert "TY  - JOUR" in ris_response.json()["content"]
    assert "ID  - doe2024local" in ris_response.json()["content"]


def test_import_bibliography_endpoint_reports_missing_file(tmp_path: Path):
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))

    response = client.post(
        "/api/imports/bibliography",
        json={"source_path": str(tmp_path / "missing.bib")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "source bibliography not found"


def test_external_search_endpoint_returns_cached_candidates(tmp_path: Path):
    discovery_client = FakeDiscoveryClient(
        [
            DiscoveryCandidate(
                source="openalex",
                external_id="W123",
                title="Local Knowledge Agents",
                authors="Jane Doe",
                year=2024,
                doi="10.1234/local",
                venue="Journal of Local Research",
                abstract="Traceable local assistants.",
                arxiv_id=None,
                pdf_url="https://example.test/local.pdf",
                landing_url="https://example.test/local",
            )
        ]
    )
    library_dir = tmp_path / "library"
    client = TestClient(
        create_app(library_dir=library_dir, discovery_client=discovery_client)
    )

    response = client.get("/api/search/external", params={"q": "local rag"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "local rag"
    assert discovery_client.queries == ["local rag"]
    result = payload["results"][0]
    assert result["id"] > 0
    assert result["source"] == "openalex"
    assert result["title"] == "Local Knowledge Agents"
    assert result["authors"] == "Jane Doe"
    assert result["pdf_url"] == "https://example.test/local.pdf"


def test_download_open_pdf_then_confirm_imports_pending_file(tmp_path: Path):
    discovery_client = FakeDiscoveryClient(
        [
            DiscoveryCandidate(
                source="openalex",
                external_id="W123",
                title="Local Knowledge Agents",
                authors="Jane Doe",
                year=2024,
                doi="10.1234/local",
                venue="Journal of Local Research",
                abstract="Traceable local assistants.",
                arxiv_id="2401.12345",
                pdf_url="https://example.test/local.pdf",
                landing_url="https://example.test/local",
            )
        ]
    )
    downloaded_urls: list[str] = []

    def pdf_downloader(url: str, target_path: Path) -> None:
        downloaded_urls.append(url)
        target_path.write_bytes(b"%PDF-1.4 downloaded pdf")

    library_dir = tmp_path / "library"
    client = TestClient(
        create_app(
            library_dir=library_dir,
            discovery_client=discovery_client,
            pdf_downloader=pdf_downloader,
        )
    )
    search_response = client.get("/api/search/external", params={"q": "local rag"})
    result_id = search_response.json()["results"][0]["id"]

    download_response = client.post(
        "/api/downloads/open-pdf",
        json={"search_result_id": result_id},
    )
    pending_path = Path(download_response.json()["pending_path"])
    import_response = client.post(
        "/api/imports/pending-download",
        json={"search_result_id": result_id, "pending_path": str(pending_path)},
    )
    list_response = client.get("/api/papers")

    assert download_response.status_code == 201
    assert downloaded_urls == ["https://example.test/local.pdf"]
    assert pending_path.exists()
    assert library_dir / "downloads" / "pending" in pending_path.parents
    assert import_response.status_code == 201
    assert import_response.json()["imported"] is True
    assert import_response.json()["paper"]["title"] == "Local Knowledge Agents"
    assert import_response.json()["paper"]["doi"] == "10.1234/local"
    paper = list_response.json()["papers"][0]
    assert paper["authors"] == "Jane Doe"
    assert paper["venue"] == "Journal of Local Research"
    assert paper["arxiv_id"] == "2401.12345"


def test_download_open_pdf_requires_pdf_url(tmp_path: Path):
    discovery_client = FakeDiscoveryClient(
        [
            DiscoveryCandidate(
                source="openalex",
                external_id="W123",
                title="Closed Paper",
                authors=None,
                year=2024,
                doi=None,
                venue=None,
                abstract=None,
                arxiv_id=None,
                pdf_url=None,
                landing_url="https://example.test/closed",
            )
        ]
    )
    library_dir = tmp_path / "library"
    client = TestClient(
        create_app(library_dir=library_dir, discovery_client=discovery_client)
    )
    search_response = client.get("/api/search/external", params={"q": "closed"})
    result_id = search_response.json()["results"][0]["id"]

    response = client.post(
        "/api/downloads/open-pdf",
        json={"search_result_id": result_id},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "search result has no open PDF URL"


def test_download_open_pdf_reports_missing_search_result(tmp_path: Path):
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))

    response = client.post(
        "/api/downloads/open-pdf",
        json={"search_result_id": 999},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "search result not found"


def test_local_search_returns_page_snippet_hits(tmp_path: Path, write_pdf):
    source = write_pdf(
        tmp_path / "Searchable Paper.pdf",
        [
            "The introduction defines retrieval augmented generation.",
            "The method evaluates contrastive retrieval over local literature.",
        ],
    )
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))
    client.post("/api/imports/pdf", json={"source_path": str(source)})

    response = client.get("/api/search/local", params={"q": "contrastive retrieval"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "contrastive retrieval"
    assert payload["hits"][0]["title"] == "Searchable Paper"
    assert payload["hits"][0]["page_number"] == 2
    assert "contrastive retrieval" in payload["hits"][0]["snippet"]


def test_reader_context_returns_current_paper_pages(tmp_path: Path, write_pdf):
    source = write_pdf(
        tmp_path / "Reader Paper.pdf",
        [
            "Page one explains the research question.",
            "Page two describes the experimental setup.",
        ],
    )
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))
    import_response = client.post("/api/imports/pdf", json={"source_path": str(source)})
    paper_id = import_response.json()["paper"]["id"]

    response = client.get(f"/api/papers/{paper_id}/reader-context")

    assert response.status_code == 200
    payload = response.json()
    assert payload["paper"]["title"] == "Reader Paper"
    assert payload["document"]["parse_status"] == "parsed"
    assert payload["document"]["page_count"] == 2
    assert payload["pages"] == [
        {"page_number": 1, "text": "Page one explains the research question."},
        {"page_number": 2, "text": "Page two describes the experimental setup."},
    ]


def test_reader_context_reports_missing_paper(tmp_path: Path):
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))

    response = client.get("/api/papers/999/reader-context")

    assert response.status_code == 404
    assert response.json()["detail"] == "paper not found"


def test_provider_settings_endpoints_hide_api_key(tmp_path: Path):
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))

    default_response = client.get("/api/settings/provider")
    save_response = client.put(
        "/api/settings/provider",
        json={
            "provider": "openai_compatible",
            "base_url": "https://api.example.test/v1",
            "model": "research-model",
            "api_key": "secret-key",
            "outbound_context_policy": "snippets_only",
        },
    )
    reload_response = client.get("/api/settings/provider")

    assert default_response.status_code == 200
    assert default_response.json()["provider"] == "none"
    assert default_response.json()["api_key_configured"] is False
    assert save_response.status_code == 200
    assert save_response.json()["api_key_configured"] is True
    assert "secret-key" not in save_response.text
    assert reload_response.json()["provider"] == "openai_compatible"
    assert reload_response.json()["api_key_configured"] is True
    assert "secret-key" not in reload_response.text


def test_ask_current_paper_returns_traceable_answer(tmp_path: Path, write_pdf):
    source = write_pdf(
        tmp_path / "Askable Paper.pdf",
        [
            "The introduction gives background.",
            "The method uses retrieval augmented generation with page citations.",
        ],
    )
    library_dir = tmp_path / "library"
    chat_provider = ApiRecordingChatProvider("它使用检索增强生成，并保留页码引用。")
    client = TestClient(create_app(library_dir=library_dir, chat_provider=chat_provider))
    import_response = client.post("/api/imports/pdf", json={"source_path": str(source)})
    paper_id = import_response.json()["paper"]["id"]
    client.put(
        "/api/settings/provider",
        json={
            "provider": "openai_compatible",
            "base_url": "https://api.example.test/v1",
            "model": "research-model",
            "api_key": "secret-key",
            "outbound_context_policy": "snippets_only",
        },
    )

    response = client.post(
        f"/api/papers/{paper_id}/assistant/ask",
        json={"question": "What method uses retrieval citations?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "它使用检索增强生成，并保留页码引用。"
    assert payload["mode"] == "strict"
    assert payload["provider"] == "openai_compatible"
    assert payload["citations"][0]["title"] == "Askable Paper"
    assert payload["citations"][0]["page_number"] == 2
    assert "retrieval augmented generation" in payload["citations"][0]["snippet"]
    prompt = chat_provider.calls[0]["messages"][1].content
    assert "The introduction gives background." not in prompt
    assert "retrieval augmented generation" in prompt


def test_ask_selected_text_returns_selection_citation(tmp_path: Path, write_pdf):
    source = write_pdf(
        tmp_path / "Selectable Paper.pdf",
        [
            "The introduction gives background.",
            "The method uses retrieval augmented generation with page citations.",
        ],
    )
    library_dir = tmp_path / "library"
    chat_provider = ApiRecordingChatProvider("Selection answer")
    client = TestClient(create_app(library_dir=library_dir, chat_provider=chat_provider))
    import_response = client.post("/api/imports/pdf", json={"source_path": str(source)})
    paper_id = import_response.json()["paper"]["id"]
    client.put(
        "/api/settings/provider",
        json={
            "provider": "openai_compatible",
            "base_url": "https://api.example.test/v1",
            "model": "research-model",
            "api_key": "secret-key",
            "outbound_context_policy": "snippets_only",
        },
    )

    response = client.post(
        f"/api/papers/{paper_id}/assistant/selection",
        json={
            "selected_text": "retrieval augmented generation",
            "page_number": 2,
            "source_span": "page:2:selection",
            "action": "translate",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Selection answer"
    assert payload["mode"] == "selection"
    assert payload["citations"][0]["chunk_id"] is None
    assert payload["citations"][0]["page_number"] == 2
    assert payload["citations"][0]["snippet"] == "retrieval augmented generation"
    assert payload["citations"][0]["source_span"] == "page:2:selection"
    prompt = chat_provider.calls[0]["messages"][1].content
    assert "retrieval augmented generation" in prompt
    assert "The introduction gives background." not in prompt


def test_notes_and_highlights_endpoints_roundtrip(tmp_path: Path):
    source = tmp_path / "Notes Paper.pdf"
    source.write_bytes(b"%PDF-1.4 notes")
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))
    import_response = client.post("/api/imports/pdf", json={"source_path": str(source)})
    paper_id = import_response.json()["paper"]["id"]

    note_response = client.post(
        "/api/notes",
        json={
            "paper_id": paper_id,
            "body": "This selected passage matters.",
            "page_number": 2,
            "source_span": "page:2:selection",
            "selected_text": "retrieval augmented generation",
            "note_type": "selection",
        },
    )
    note_id = note_response.json()["id"]
    highlight_response = client.post(
        "/api/highlights",
        json={
            "paper_id": paper_id,
            "page_number": 2,
            "source_span": "page:2:selection",
            "selected_text": "retrieval augmented generation",
            "color": "yellow",
            "note_id": note_id,
        },
    )
    notes_response = client.get(f"/api/papers/{paper_id}/notes")
    highlights_response = client.get(f"/api/papers/{paper_id}/highlights")

    assert note_response.status_code == 201
    assert note_response.json()["body"] == "This selected passage matters."
    assert note_response.json()["selected_text"] == "retrieval augmented generation"
    assert highlight_response.status_code == 201
    assert highlight_response.json()["note_id"] == note_id
    assert notes_response.status_code == 200
    assert notes_response.json()["notes"][0]["id"] == note_id
    assert highlights_response.status_code == 200
    assert highlights_response.json()["highlights"][0]["page_number"] == 2


def test_ask_selected_text_reports_missing_paper(tmp_path: Path):
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))

    response = client.post(
        "/api/papers/999/assistant/selection",
        json={
            "selected_text": "important claim",
            "page_number": 1,
            "source_span": "page:1:selection",
            "action": "explain",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "paper not found"


def test_ask_current_paper_requires_provider_settings(tmp_path: Path, write_pdf):
    source = write_pdf(
        tmp_path / "Unconfigured Paper.pdf",
        ["The method uses retrieval augmented generation."],
    )
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))
    import_response = client.post("/api/imports/pdf", json={"source_path": str(source)})
    paper_id = import_response.json()["paper"]["id"]

    response = client.post(
        f"/api/papers/{paper_id}/assistant/ask",
        json={"question": "What method is used?"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "model provider not configured"


def test_ask_current_paper_reports_missing_paper(tmp_path: Path):
    library_dir = tmp_path / "library"
    client = TestClient(create_app(library_dir=library_dir))

    response = client.post(
        "/api/papers/999/assistant/ask",
        json={"question": "What is this paper about?"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "paper not found"
