"""MemoryManager — orchestrates conversation and long-term memory systems."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from nico.memory.conversation import ConversationMemory
from nico.memory.embeddings import EmbeddingProvider
from nico.memory.long_term import LongTermMemory
from nico.memory.persistence import MemoryStore

_MISSING = object()

_logger = logging.getLogger("nico.memory.manager")

# Important keywords that signal facts worth consolidating
_CONSOLIDATION_KEYWORDS = [
    "my name is", "i am", "i'm", "i live", "i work", "i like",
    "i love", "i hate", "i prefer", "my favorite", "my favourite",
    "remember", "don't forget", "important", "call me", "my email",
    "my phone", "my address", "i have a", "i need", "i want",
]


@dataclass
class MemoryManager:
    """Orchestrates conversation and long-term memory with consolidation.

    Provides a unified API for:
    - Storing conversation turns with automatic importance scoring
    - Consolidating important facts from conversations to long-term memory
    - Keyword and semantic search across all stored knowledge
    - User preference management
    """

    conversation: ConversationMemory = field(default_factory=ConversationMemory)
    long_term: LongTermMemory = field(default_factory=LongTermMemory)
    embedding_provider: EmbeddingProvider | None = None
    conversation_store: MemoryStore | None = None
    long_term_store: MemoryStore | None = None

    def __post_init__(self) -> None:
        if self.embedding_provider and not self.long_term.embedding_provider:
            self.long_term.embedding_provider = self.embedding_provider
        if self.conversation_store is not None and self.conversation.store is None:
            self.conversation.store = self.conversation_store
        if self.long_term_store is not None and self.long_term.store is None:
            self.long_term.store = self.long_term_store

    # ------------------------------------------------------------------
    # Conversation management
    # ------------------------------------------------------------------

    def add_turn(self, role: str, content: str) -> None:
        """Record a conversation turn with automatic importance scoring.

        Also triggers consolidation: if the message contains facts worth
        remembering, they are extracted to long-term memory.
        """
        importance = ConversationMemory.score_importance(role, content)
        self.conversation.add_message(role, content, importance=importance)
        self._consolidate(role, content, importance)

    def recent_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent conversation history for provider context."""
        return self.conversation.to_provider_history(limit=limit)

    def conversation_summary(self) -> str:
        """Return a text summary of the current conversation."""
        return self.conversation.summary()

    # ------------------------------------------------------------------
    # Long-term memory
    # ------------------------------------------------------------------

    def remember(
        self,
        key: str,
        value: Any,
        *,
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> None:
        """Store a fact in long-term memory."""
        self.long_term.remember(key, value, importance=importance, tags=tags)

    def recall(self, key: str, default: Any | None = None) -> Any:
        """Retrieve a fact by exact key."""
        return self.long_term.recall(key, default)

    def search(
        self,
        query: str,
        *,
        semantic: bool = False,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search both keyword and optionally semantic across long-term memory."""
        return self.long_term.search(query, semantic=semantic, top_k=top_k)

    def get_preferences(self) -> dict[str, Any]:
        """Return all stored user preferences."""
        return self.long_term.get_preferences()

    def set_preference(self, key: str, value: Any) -> None:
        """Store a user preference."""
        self.long_term.set_preference(key, value)

    # ------------------------------------------------------------------
    # Consolidation
    # ------------------------------------------------------------------

    def _consolidate(self, role: str, content: str, importance: float) -> None:
        """Extract important facts from a message and store in long-term memory.

        Uses keyword heuristics to detect facts the user explicitly stated.
        """
        if role != "user":
            return

        lower = content.lower()

        # Detect name declarations: "my name is X" or "call me X"
        for pattern in _CONSOLIDATION_KEYWORDS:
            if pattern not in lower:
                continue

            if "my name is" in lower:
                val = content[lower.index("my name is") + len("my name is"):].strip().rstrip(".,!?")
                self.long_term.remember("user_name", val, importance=0.95, tags=["preference", "identity"])
                _logger.info("Consolidated user_name: %s", val)

            if "call me" in lower:
                idx = lower.index("call me") + len("call me")
                val = content[idx:].strip().rstrip(".,!?")
                # Take only first few words
                val = val.split()[0] if val.split() else val
                self.long_term.remember("user_name_preferred", val, importance=0.9, tags=["preference", "identity"])
                _logger.info("Consolidated preferred_name: %s", val)

            if "i live in" in lower or "i am from" in lower or "i'm from" in lower:
                for p in ["i live in", "i am from", "i'm from"]:
                    if p in lower:
                        idx = lower.index(p) + len(p)
                        val = content[idx:].strip().rstrip(".,!?")
                        self.long_term.remember("user_location", val, importance=0.85, tags=["preference", "location"])
                        _logger.info("Consolidated location: %s", val)
                        break

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Explicitly persist both conversation and long-term memory stores."""
        self.conversation.save()
        self.long_term.save()

    def attach_stores(
        self,
        conversation_store: MemoryStore | None = None,
        long_term_store: MemoryStore | None = None,
    ) -> None:
        """Attach persistent stores to both memory backends."""
        if conversation_store is not None:
            self.conversation.store = conversation_store
            self.conversation_store = conversation_store
        if long_term_store is not None:
            self.long_term.store = long_term_store
            self.long_term_store = long_term_store

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def clear_conversation(self) -> None:
        """Clear the current conversation history."""
        self.conversation.clear()

    def reset_all(self) -> None:
        """Clear all memories (conversation + long-term)."""
        self.conversation.clear()
        self.long_term.reset()

    def prune_long_term(self, keep_top_n: int = 100) -> int:
        """Remove least important long-term facts, returns count removed."""
        return self.long_term.prune(keep_top_n=keep_top_n)

    async def index_embeddings(self) -> int:
        """Pre-compute embeddings for all long-term facts. Returns count indexed."""
        return await self.long_term.index_facts()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def from_stores(
        cls,
        conversation_store: MemoryStore,
        long_term_store: MemoryStore,
        max_chars: int = 8000,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> "MemoryManager":
        """Load both memory systems from persistent stores."""
        conv = ConversationMemory.from_store(conversation_store, max_chars=max_chars)
        lt = LongTermMemory.from_store(long_term_store, embedding_provider=embedding_provider)
        return cls(
            conversation=conv,
            long_term=lt,
            embedding_provider=embedding_provider,
            conversation_store=conversation_store,
            long_term_store=long_term_store,
        )
