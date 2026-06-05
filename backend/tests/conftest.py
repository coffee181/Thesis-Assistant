from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def write_pdf() -> Callable[[Path, list[str]], Path]:
    def _write_pdf(path: Path, pages: list[str]) -> Path:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        path.parent.mkdir(parents=True, exist_ok=True)
        pdf = canvas.Canvas(str(path), pagesize=letter)
        for page_text in pages:
            text = pdf.beginText(72, 720)
            for line in page_text.splitlines() or [""]:
                text.textLine(line)
            pdf.drawText(text)
            pdf.showPage()
        pdf.save()
        return path

    return _write_pdf
