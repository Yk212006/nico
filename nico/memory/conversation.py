from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nico.memory.persistence import MemoryStore


@dataclass
class ConversationMemory:
    """Stores the active conversation transcript with automatic summarization.

    When the accumulated content grows beyond ``max_chars`` the oldest
    messages are replaced with a concise summary, keeping the active window
    small enough for provider context windows while preserving semantic
    continuity.
    """

    messages: list[dict[str, Any]] = field(default_factory=list)
    store: MemoryStore | None = None
    max_chars: int = 8000
    _summary: str = field(default="", init=False, repr=False)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def add_message(self, role: str, content: str, *, importance: float = 0.5) -> None:
        """Append a message and persist it.

        Args:
            role:       ``"user"`` | ``"assistant"`` | ``"system"``
            content:    The message body.
            importance: Importance score 0.0–1.0.  Used when pruning to
                        prefer keeping high-importance messages.
        """
        self.messages.append(
            {"role": role, "content": content, "importance": importance}
        )
        self._maybe_summarize()
        if self.store is not None:
            self.store.save({"messages": self.messages, "summary": self._summary})

    def clear(self) -> None:
        """Clear all messages and the summary."""
        self.messages.clear()
        self._summary = ""
        if self.store is not None:
            self.store.save({"messages": [], "summary": ""})

    def recent_messages(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return the *limit* most recent messages, stripping the importance key."""
        recents = self.messages[-limit:] if limit > 0 else []
        return [{"role": m["role"], "content": m["content"]} for m in recents]

    def to_provider_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return a clean history list suitable for provider ``history`` params.

        If a summary exists it is prepended as a ``"system"`` message so the
        model has context for pruned turns.
        """
        history: list[dict[str, Any]] = []
        if self._summary:
            history.append(
                {
                    "role": "system",
                    "content": f"[Earlier conversation summary: {self._summary}]",
                }
            )
        history.extend(self.recent_messages(limit))
        return history

    def summary(self) -> str:
        """Return a human-readable transcript of all messages."""
        return "\n".join(
            f"{m['role']}: {m['content']}" for m in self.messages
        )

    # ------------------------------------------------------------------
    # Importance scoring
    # ------------------------------------------------------------------

    @staticmethod
    def score_importance(role: str, content: str) -> float:
        """Heuristic importance scorer (0.0–1.0).

        Rules:
        - Questions score higher (0.7) because they signal new information needs.
        - Short assistant acknowledgements score lower (0.3).
        - Everything else scores 0.5.
        """
        if role == "user" and "?" in content:
            return 0.7
        if role == "assistant" and len(content) < 40:
            return 0.3
        return 0.5

    # ------------------------------------------------------------------
    # Auto-summarization
    # ------------------------------------------------------------------

    def _total_chars(self) -> int:
        return sum(len(m.get("content", "")) for m in self.messages)

    def _maybe_summarize(self) -> None:
        """Prune low-importance old messages once the buffer grows too large."""
        if self._total_chars() <= self.max_chars:
            return

        # Keep the most recent half of messages
        keep_count = max(4, len(self.messages) // 2)
        old_messages = self.messages[:-keep_count]
        self.messages = self.messages[-keep_count:]

        # Build a brief summary of pruned messages
        lines = [f"{m['role']}: {m['content'][:100]}" for m in old_messages]
        pruned_summary = "; ".join(lines)
        if self._summary:
            self._summary = f"{self._summary} | {pruned_summary}"
        else:
            self._summary = pruned_summary

    # ------------------------------------------------------------------
    # Persistence loading
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Explicitly persist the current state to the store."""
        if self.store is not None:
            self.store.save({"messages": self.messages, "summary": self._summary})

    @classmethod
    def from_store(cls, store: MemoryStore, max_chars: int = 8000) -> "ConversationMemory":
        """Load a ConversationMemory from a persistent store."""
        data = store.load()
        instance = cls(store=store, max_chars=max_chars)
        instance.messages = data.get("messages", [])
        instance._summary = data.get("summary", "")
        return instance
