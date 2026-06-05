from pathlib import Path

from fastapi.testclient import TestClient

from knowledge_agent.main import create_app


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
