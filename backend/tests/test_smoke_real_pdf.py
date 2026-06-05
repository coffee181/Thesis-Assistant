import importlib.util
from pathlib import Path

from knowledge_agent.providers import ProviderMessage


def load_smoke_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "smoke_real_pdf.py"
    assert script_path.exists(), "scripts/smoke_real_pdf.py is missing"
    spec = importlib.util.spec_from_file_location("smoke_real_pdf", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeChatProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def complete(self, settings, messages: list[ProviderMessage]) -> str:
        self.calls.append({"settings": settings, "messages": messages})
        return "这篇论文使用可追溯的当前文献片段回答问题。[S1]"


def test_build_settings_from_env_reads_provider_settings():
    smoke = load_smoke_module()

    config = smoke.build_settings_from_env(
        {
            "KA_SMOKE_PDF": "F:\\knowledge-agent\\2301.12652v4.pdf",
            "KA_SMOKE_BASE_URL": "https://api.example.test/",
            "KA_SMOKE_MODEL": "research-model",
            "KA_SMOKE_API_KEY": "secret-key",
            "KA_SMOKE_PROXY_URL": "http://127.0.0.1:7897",
            "KA_SMOKE_LIBRARY_DIR": "F:\\knowledge-agent\\.smoke-library",
            "KA_SMOKE_QUESTION": "请概括这篇论文的方法。",
        }
    )

    assert config.pdf_path == Path("F:\\knowledge-agent\\2301.12652v4.pdf")
    assert config.base_url == "https://api.example.test/"
    assert config.model == "research-model"
    assert config.api_key == "secret-key"
    assert config.proxy_url == "http://127.0.0.1:7897"
    assert config.library_dir == Path("F:\\knowledge-agent\\.smoke-library")
    assert config.question == "请概括这篇论文的方法。"


def test_run_smoke_imports_pdf_and_asks_current_paper(tmp_path: Path, write_pdf):
    smoke = load_smoke_module()
    pdf_path = write_pdf(
        tmp_path / "Real Smoke.pdf",
        [
            "The paper proposes a retrieval augmented reading assistant.",
            "The method grounds answers in page citations.",
        ],
    )
    chat_provider = FakeChatProvider()

    result = smoke.run_smoke(
        smoke.SmokeConfig(
            pdf_path=pdf_path,
            base_url="https://api.example.test/",
            model="research-model",
            api_key="secret-key",
            proxy_url=None,
            library_dir=tmp_path / "library",
            question="What method is used?",
        ),
        chat_provider=chat_provider,
    )

    assert result.paper_title == "Real Smoke"
    assert result.page_count == 2
    assert result.citation_count > 0
    assert result.answer_preview.startswith("这篇论文")
    assert chat_provider.calls[0]["settings"].base_url == "https://api.example.test/"
    prompt = chat_provider.calls[0]["messages"][1].content
    assert "Current Paper: Real Smoke" in prompt
    assert "page citations" in prompt


def test_main_returns_2_for_missing_pdf(tmp_path: Path, monkeypatch, capsys):
    smoke = load_smoke_module()
    monkeypatch.setenv("KA_SMOKE_PDF", str(tmp_path / "missing.pdf"))
    monkeypatch.setenv("KA_SMOKE_BASE_URL", "https://api.example.test/")
    monkeypatch.setenv("KA_SMOKE_MODEL", "research-model")
    monkeypatch.setenv("KA_SMOKE_API_KEY", "secret-key")

    exit_code = smoke.main([])

    assert exit_code == 2
    assert "PDF not found" in capsys.readouterr().err
