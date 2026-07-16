"""Embedding provider interface and implementations for semantic memory search."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

_logger = logging.getLogger("nico.memory.embeddings")

try:
    import httpx
    _HTTPX = True
except ModuleNotFoundError:
    _HTTPX = False


class EmbeddingProvider(ABC):
    """Abstract interface for generating text embeddings."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text."""

    @abstractmethod
    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts."""


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding API provider using text-embedding-3-small."""

    MODEL = "text-embedding-3-small"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    async def embed(self, text: str) -> list[float]:
        results = await self.embed_many([text])
        return results[0] if results else []

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key or not _HTTPX:
            return self._stub_embeddings(texts)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": self.MODEL, "input": texts},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                results: list[tuple[int, list[float]]] = []
                for item in data.get("data", []):
                    results.append((item["index"], item["embedding"]))
                results.sort(key=lambda x: x[0])
                return [r[1] for r in results]
        except Exception as exc:
            _logger.warning("OpenAI embedding failed: %s", exc)
            return self._stub_embeddings(texts)

    @staticmethod
    def _stub_embeddings(texts: list[str]) -> list[list[float]]:
        """Return deterministic pseudo-embeddings when API is unavailable."""
        rng = _DeterministicRNG(42)
        return [[rng.next() for _ in range(128)] for _ in texts]


class _DeterministicRNG:
    """Simple deterministic pseudo-random for reproducible stub embeddings."""

    def __init__(self, seed: int) -> None:
        self._state = seed

    def next(self) -> float:
        self._state = (self._state * 1103515245 + 12345) & 0x7FFFFFFF
        return (self._state & 0xFFFF) / 65535.0


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingCache:
    """Local cache for embeddings to avoid redundant API calls.

    Cache is stored as a JSON file keyed by a hash of the input text.
    """

    def __init__(self, cache_path: str | Path | None = None) -> None:
        cache_dir = os.getenv("NICO_MEMORY_DIR", "~/.nico/memory")
        path = cache_path or Path(cache_dir).expanduser() / "embedding_cache.json"
        self._path = Path(path)
        self._cache: dict[str, list[float]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._cache = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                self._cache = {}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._cache), encoding="utf-8")
        except Exception as exc:
            _logger.warning("Failed to save embedding cache: %s", exc)

    def _key(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> list[float] | None:
        return self._cache.get(self._key(text))

    def set(self, text: str, embedding: list[float]) -> None:
        self._cache[self._key(text)] = embedding
        self._save()

    def clear(self) -> None:
        self._cache.clear()
        if self._path.exists():
            self._path.unlink()
