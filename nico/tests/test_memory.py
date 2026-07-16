import json
from pathlib import Path

from nico.memory.conversation import ConversationMemory
from nico.memory.long_term import LongTermMemory
from nico.memory.persistence import FileMemoryStore, MemoryStore


def test_conversation_memory_tracks_messages() -> None:
    memory = ConversationMemory()
    memory.add_message("user", "hello")

    assert memory.messages[-1]["content"] == "hello"


def test_long_term_memory_remembers_facts() -> None:
    memory = LongTermMemory()
    memory.remember("name", "NICO")

    assert memory.recall("name") == "NICO"


def test_file_memory_store_persists_and_loads(tmp_path: Path) -> None:
    store = FileMemoryStore(tmp_path / "memory.json")
    store.save({"key": "value"})
    loaded = store.load()

    assert loaded == {"key": "value"}
