from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from nico.memory.embeddings import EmbeddingProvider, cosine_similarity
from nico.memory.persistence import MemoryStore


@dataclass
class LongTermMemory:
    """Stores durable user preferences and facts with keyword + semantic search.

    Facts are stored as a flat key→value dictionary.  Each fact also
    carries metadata (timestamp, importance, tags) so callers can later
    build a richer retrieval layer on top.

    When an :class:`EmbeddingProvider` is configured, :meth:`search` can
    optionally perform semantic (cosine similarity) matching in addition
    to keyword matching.
    """

    facts: dict[str, Any] = field(default_factory=dict)
    _meta: dict[str, dict[str, Any]] = field(default_factory=dict, init=False, repr=False)
    _embeddings: dict[str, list[float]] = field(default_factory=dict, init=False, repr=False)
    store: MemoryStore | None = None
    embedding_provider: EmbeddingProvider | None = None

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    def remember(
        self,
        key: str,
        value: Any,
        *,
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> None:
        """Store or update a fact.

        Args:
            key:        Unique identifier for the fact.
            value:      The value to store (any JSON-serialisable type).
            importance: 0.0–1.0; higher values are preserved when pruning.
            tags:       Optional list of topic tags for future search.
        """
        self.facts[key] = value
        self._meta[key] = {
            "stored_at": time.time(),
            "importance": importance,
            "tags": tags or [],
        }
        self.save()

    def recall(self, key: str, default: Any | None = None) -> Any:
        """Retrieve a fact by exact key, returning *default* if not found."""
        return self.facts.get(key, default)

    def forget(self, key: str) -> bool:
        """Remove a fact.  Returns ``True`` if the key existed."""
        existed = key in self.facts
        self.facts.pop(key, None)
        self._meta.pop(key, None)
        self._embeddings.pop(key, None)
        if existed:
            self.save()
        return existed

    def update(self, key: str, value: Any) -> None:
        """Update an existing fact's value while keeping its metadata."""
        existing_meta = self._meta.get(key, {})
        self.remember(
            key,
            value,
            importance=existing_meta.get("importance", 0.5),
            tags=existing_meta.get("tags", []),
        )

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_facts(self) -> dict[str, Any]:
        """Return a snapshot of all stored facts."""
        return dict(self.facts)

    def search(
        self,
        query: str,
        *,
        semantic: bool = False,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search stored facts by keyword and optionally by semantic similarity.

        Args:
            query:     Search query string.
            semantic:  If ``True``, also perform embedding-based cosine similarity.
            top_k:     Maximum number of results when using semantic search.
            min_score: Minimum similarity score (0.0–1.0) for semantic results.

        Returns:
            List of ``{"key": ..., "value": ..., "meta": ..., "score": ...}`` dicts
            ordered by relevance (descending).
        """
        results = self._keyword_search(query)

        if semantic and self.embedding_provider is not None:
            semantic_results = self._semantic_search(query, top_k, min_score)
            merged = {r["key"]: r for r in results}
            for sr in semantic_results:
                if sr["key"] in merged:
                    merged[sr["key"]]["score"] = max(
                        merged[sr["key"]].get("score", 0.0), sr.get("score", 0.0)
                    )
                else:
                    merged[sr["key"]] = sr
            results = sorted(merged.values(), key=lambda r: r.get("score", 0.0), reverse=True)

        return results

    def _keyword_search(self, query: str) -> list[dict[str, Any]]:
        q = query.lower()
        results: list[dict[str, Any]] = []
        for key, value in self.facts.items():
            hit = q in key.lower() or (isinstance(value, str) and q in value.lower())
            if not hit and self._meta.get(key, {}).get("tags"):
                hit = any(q in tag.lower() for tag in self._meta[key]["tags"])
            if hit:
                results.append(
                    {
                        "key": key,
                        "value": value,
                        "meta": self._meta.get(key, {}),
                        "score": 1.0,
                    }
                )
        results.sort(key=lambda r: r["meta"].get("importance", 0.5), reverse=True)
        return results

    def _semantic_search(self, query: str, top_k: int, min_score: float) -> list[dict[str, Any]]:
        import asyncio

        query_emb = asyncio.run(self._get_embedding(query))
        if not query_emb:
            return []

        scored: list[tuple[str, float]] = []
        for key in self.facts:
            key_emb = self._get_cached_embedding(key)
            if key_emb is None:
                continue
            score = cosine_similarity(query_emb, key_emb)
            if score >= min_score:
                scored.append((key, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        results = []
        for key, score in scored[:top_k]:
            results.append(
                {
                    "key": key,
                    "value": self.facts[key],
                    "meta": self._meta.get(key, {}),
                    "score": round(score, 4),
                }
            )
        return results

    def _get_cached_embedding(self, key: str) -> list[float] | None:
        return self._embeddings.get(key)

    async def _get_embedding(self, text: str) -> list[float]:
        if self.embedding_provider is None:
            return []
        try:
            return await self.embedding_provider.embed(text)
        except Exception:
            return []

    async def index_facts(self) -> int:
        """Pre-compute and cache embeddings for all stored facts.

        Returns the number of facts indexed.
        """
        if self.embedding_provider is None:
            return 0

        texts: list[str] = []
        keys: list[str] = []
        for key, value in self.facts.items():
            if key not in self._embeddings:
                texts.append(f"{key}: {value}")
                keys.append(key)

        if not texts:
            return len(self._embeddings)

        embeddings = await self.embedding_provider.embed_many(texts)
        for key, emb in zip(keys, embeddings, strict=False):
            self._embeddings[key] = emb

        return len(embeddings)

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    def get_preferences(self) -> dict[str, Any]:
        """Return all facts tagged with ``"preference"`` as a flat dict."""
        prefs: dict[str, Any] = {}
        for key, value in self.facts.items():
            meta = self._meta.get(key, {})
            if "preference" in meta.get("tags", []):
                prefs[key] = value
        return prefs

    def set_preference(self, key: str, value: Any) -> None:
        """Store a user preference (tags it with ``"preference"``)."""
        existing = self._meta.get(key, {})
        tags = list(set(existing.get("tags", []) + ["preference"]))
        self.remember(key, value, importance=0.9, tags=tags)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Erase all stored facts and metadata."""
        self.facts.clear()
        self._meta.clear()
        self._embeddings.clear()
        self.save()

    def prune(self, keep_top_n: int = 100) -> int:
        """Remove the least important facts beyond *keep_top_n*.

        Returns the number of facts removed.
        """
        if len(self.facts) <= keep_top_n:
            return 0

        ranked = sorted(
            self.facts.keys(),
            key=lambda k: self._meta.get(k, {}).get("importance", 0.5),
            reverse=True,
        )
        to_remove = ranked[keep_top_n:]
        for key in to_remove:
            self.facts.pop(key, None)
            self._meta.pop(key, None)
            self._embeddings.pop(key, None)
        if to_remove:
            self.save()
        return len(to_remove)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Explicitly persist the current state to the store."""
        if self.store is not None:
            self.store.save({
                "facts": self.facts,
                "meta": self._meta,
                "embeddings": self._embeddings,
            })

    @classmethod
    def from_store(
        cls,
        store: MemoryStore,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> "LongTermMemory":
        """Load a LongTermMemory from a persistent store."""
        data = store.load()
        instance = cls(store=store, embedding_provider=embedding_provider)
        instance.facts = data.get("facts", {})
        instance._meta = data.get("meta", {})
        instance._embeddings = data.get("embeddings", {})
        return instance
