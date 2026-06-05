import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path


LOCAL_EMBEDDING_MODEL = "local-hashing-v1"
DEFAULT_DIMENSIONS = 128


@dataclass(frozen=True)
class EmbeddedText:
    values: tuple[float, ...]

    def similarity(self, other: "EmbeddedText") -> float:
        return sum(left * right for left, right in zip(self.values, other.values))


@dataclass(frozen=True)
class VectorSearchResult:
    chunk_id: int
    score: float


@dataclass(frozen=True)
class _VectorEntry:
    vector_id: str
    document_id: int
    chunk_id: int
    text: str
    vector: tuple[float, ...]


def embed_text(text: str, dimensions: int = DEFAULT_DIMENSIONS) -> EmbeddedText:
    if dimensions <= 0:
        raise ValueError("dimensions must be positive")

    values = [0.0] * dimensions
    for token in _tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        values[index] += 1.0

    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return EmbeddedText(tuple(values))
    return EmbeddedText(tuple(value / norm for value in values))


class LocalVectorIndex:
    def __init__(self, index_path: Path) -> None:
        self._index_path = index_path

    def replace_document_entries(
        self,
        document_id: int,
        entries: list[tuple[int, str]],
    ) -> list[tuple[int, str, str]]:
        current_entries = [
            entry
            for entry in self._load_entries()
            if entry.document_id != document_id
        ]
        mappings: list[tuple[int, str, str]] = []
        for chunk_id, text in entries:
            vector_id = _vector_id(document_id, chunk_id)
            current_entries.append(
                _VectorEntry(
                    vector_id=vector_id,
                    document_id=document_id,
                    chunk_id=chunk_id,
                    text=text,
                    vector=embed_text(text).values,
                )
            )
            mappings.append((chunk_id, vector_id, LOCAL_EMBEDDING_MODEL))
        self._save_entries(current_entries)
        return mappings

    def delete_document(self, document_id: int) -> None:
        entries = [
            entry
            for entry in self._load_entries()
            if entry.document_id != document_id
        ]
        self._save_entries(entries)

    def search(self, query: str, limit: int = 10) -> list[VectorSearchResult]:
        if limit <= 0:
            return []
        query_vector = embed_text(query)
        scored = [
            VectorSearchResult(
                chunk_id=entry.chunk_id,
                score=query_vector.similarity(EmbeddedText(entry.vector)),
            )
            for entry in self._load_entries()
        ]
        return [
            result
            for result in sorted(scored, key=lambda result: result.score, reverse=True)
            if result.score > 0
        ][:limit]

    def _load_entries(self) -> list[_VectorEntry]:
        if not self._index_path.exists():
            return []
        try:
            payload = json.loads(self._index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        entries = payload.get("entries") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return []
        return [
            _entry_from_payload(entry)
            for entry in entries
            if _entry_from_payload(entry) is not None
        ]

    def _save_entries(self, entries: list[_VectorEntry]) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "model": LOCAL_EMBEDDING_MODEL,
            "dimensions": DEFAULT_DIMENSIONS,
            "entries": [
                {
                    "vector_id": entry.vector_id,
                    "document_id": entry.document_id,
                    "chunk_id": entry.chunk_id,
                    "text": entry.text,
                    "vector": list(entry.vector),
                }
                for entry in entries
            ],
        }
        self._index_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )


def _entry_from_payload(value: object) -> _VectorEntry | None:
    if not isinstance(value, dict):
        return None
    vector = value.get("vector")
    if not isinstance(vector, list):
        return None
    try:
        return _VectorEntry(
            vector_id=str(value["vector_id"]),
            document_id=int(value["document_id"]),
            chunk_id=int(value["chunk_id"]),
            text=str(value["text"]),
            vector=tuple(float(item) for item in vector),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _vector_id(document_id: int, chunk_id: int) -> str:
    return f"document:{document_id}:chunk:{chunk_id}"
