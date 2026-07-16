from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


class MemoryStore(Protocol):
    """Protocol for persistence backends for memory data."""

    def save(self, data: dict[str, Any]) -> None:
        ...

    def load(self) -> dict[str, Any]:
        ...


class FileMemoryStore:
    """A simple filesystem-backed memory store for development and testing."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))
