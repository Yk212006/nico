from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationContext:
    """Tracks lightweight conversation context across turns."""

    last_topic: str | None = None
    last_user_message: str | None = None
    followup_count: int = 0
    start_time: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    async def update(self, message: str) -> None:
        self.last_user_message = message
        lowered = message.lower()
        if "weather" in lowered:
            self.last_topic = "weather"
        elif "email" in lowered or "gmail" in lowered:
            self.last_topic = "email"
        elif "light" in lowered or "home" in lowered:
            self.last_topic = "home"
        elif "shutdown" in lowered or "restart" in lowered:
            self.last_topic = "system"
        elif "file" in lowered or "read" in lowered or "write" in lowered:
            self.last_topic = "files"
        elif "gpio" in lowered or "pin" in lowered:
            self.last_topic = "gpio"
        elif "news" in lowered or "headline" in lowered:
            self.last_topic = "news"
        elif self.last_topic is not None:
            pass
        else:
            self.last_topic = "general"
        self.followup_count += 1
        self.metadata["last_turn"] = message
        self.metadata["last_turn_time"] = time.time()

    def summary(self) -> str:
        return (
            f"topic={self.last_topic or 'general'} "
            f"followups={self.followup_count} "
            f"last_message={self.last_user_message or ''}"
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "last_topic": self.last_topic,
            "last_user_message": self.last_user_message,
            "followup_count": self.followup_count,
            "start_time": self.start_time,
            "duration_seconds": round(time.time() - self.start_time, 2),
            "metadata": dict(self.metadata),
        }
