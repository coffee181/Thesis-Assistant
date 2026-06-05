import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    library_dir: Path

    @property
    def database_path(self) -> Path:
        return self.library_dir / "database.sqlite"


def load_config(library_dir: Path | None = None) -> AppConfig:
    configured = library_dir or Path(
        os.environ.get("KA_LIBRARY_DIR", Path.home() / "KnowledgeAgentLibrary")
    )
    return AppConfig(library_dir=configured)
