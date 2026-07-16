from pathlib import Path

from nico.memory.conversation import ConversationMemory
from nico.memory.long_term import LongTermMemory
from nico.memory.persistence import FileMemoryStore


def test_conversation_memory_supports_summary_and_recent_messages(tmp_path: Path) -> None:
    memory = ConversationMemory(store=FileMemoryStore(tmp_path / "memory.json"))
    memory.add_message("user", "hello")
    memory.add_message("assistant", "hi there")

    assert memory.recent_messages(1)[0]["content"] == "hi there"
    assert memory.summary() == "user: hello\nassistant: hi there"


def test_long_term_memory_supports_listing_and_reset() -> None:
    memory = LongTermMemory()
    memory.remember("name", "NICO")
    memory.remember("status", "active")

    assert memory.list_facts() == {"name": "NICO", "status": "active"}
    memory.reset()
    assert memory.recall("name") is None
