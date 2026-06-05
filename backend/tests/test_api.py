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
