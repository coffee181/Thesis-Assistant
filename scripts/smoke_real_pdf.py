import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from fastapi.testclient import TestClient

from knowledge_agent.main import create_app


DEFAULT_QUESTION = "请基于当前论文的已抽取内容，概括这篇论文的核心方法，并给出页码引用。"


@dataclass(frozen=True)
class SmokeConfig:
    pdf_path: Path
    base_url: str
    model: str
    api_key: str
    proxy_url: str | None
    library_dir: Path | None
    question: str


@dataclass(frozen=True)
class SmokeResult:
    paper_title: str
    paper_id: int
    page_count: int
    citation_count: int
    provider: str
    answer_preview: str
    library_dir: str


def build_settings_from_env(env: Mapping[str, str]) -> SmokeConfig:
    return SmokeConfig(
        pdf_path=Path(_required_env(env, "KA_SMOKE_PDF")),
        base_url=_required_env(env, "KA_SMOKE_BASE_URL"),
        model=_required_env(env, "KA_SMOKE_MODEL"),
        api_key=_required_env(env, "KA_SMOKE_API_KEY"),
        proxy_url=_optional_env(env, "KA_SMOKE_PROXY_URL"),
        library_dir=(
            Path(library_dir)
            if (library_dir := _optional_env(env, "KA_SMOKE_LIBRARY_DIR")) is not None
            else None
        ),
        question=env.get("KA_SMOKE_QUESTION", DEFAULT_QUESTION).strip() or DEFAULT_QUESTION,
    )


def run_smoke(config: SmokeConfig, chat_provider=None) -> SmokeResult:
    if not config.pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {config.pdf_path}")
    if not config.pdf_path.is_file():
        raise ValueError(f"PDF path is not a file: {config.pdf_path}")

    if config.library_dir is None:
        with tempfile.TemporaryDirectory(prefix="knowledge-agent-smoke-") as temp_dir:
            return _run_smoke_with_library(
                config=config,
                library_dir=Path(temp_dir),
                chat_provider=chat_provider,
            )

    return _run_smoke_with_library(
        config=config,
        library_dir=config.library_dir,
        chat_provider=chat_provider,
    )


def main(argv: list[str] | None = None) -> int:
    _ = argv
    try:
        config = build_settings_from_env(os.environ)
        result = run_smoke(config)
    except (KeyError, FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0


def _run_smoke_with_library(
    config: SmokeConfig,
    library_dir: Path,
    chat_provider,
) -> SmokeResult:
    client = TestClient(create_app(library_dir=library_dir, chat_provider=chat_provider))

    import_response = client.post(
        "/api/imports/pdf",
        json={"source_path": str(config.pdf_path)},
    )
    _raise_for_smoke_failure("PDF import failed", import_response)
    paper = import_response.json()["paper"]
    paper_id = int(paper["id"])

    context_response = client.get(f"/api/papers/{paper_id}/reader-context")
    _raise_for_smoke_failure("Reader context failed", context_response)
    context = context_response.json()
    pages = context["pages"]
    page_count = int(context["document"]["page_count"] or len(pages))
    if page_count <= 0 or not pages:
        raise RuntimeError("PDF import succeeded but no extracted page text is available")

    settings_response = client.put(
        "/api/settings/provider",
        json={
            "provider": "openai_compatible",
            "base_url": config.base_url,
            "model": config.model,
            "api_key": config.api_key,
            "outbound_context_policy": "snippets_only",
            "proxy_url": config.proxy_url,
        },
    )
    _raise_for_smoke_failure("Provider settings failed", settings_response)

    ask_response = client.post(
        f"/api/papers/{paper_id}/assistant/ask",
        json={"question": config.question},
    )
    _raise_for_smoke_failure("Assistant question failed", ask_response)
    answer = ask_response.json()
    citations = answer["citations"]
    if not citations:
        raise RuntimeError("Assistant answered without citations")

    return SmokeResult(
        paper_title=str(paper["title"]),
        paper_id=paper_id,
        page_count=page_count,
        citation_count=len(citations),
        provider=str(answer["provider"]),
        answer_preview=str(answer["answer"])[:300],
        library_dir=str(library_dir),
    )


def _required_env(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise KeyError(f"{key} is required")
    return value


def _optional_env(env: Mapping[str, str], key: str) -> str | None:
    value = env.get(key, "").strip()
    return value or None


def _raise_for_smoke_failure(label: str, response) -> None:
    if response.status_code < 400:
        return
    detail = response.text
    try:
        detail = response.json().get("detail", detail)
    except ValueError:
        pass
    raise RuntimeError(f"{label}: {response.status_code} {detail}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
