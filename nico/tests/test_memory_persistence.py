import tempfile
from pathlib import Path

from nico.memory.conversation import ConversationMemory
from nico.memory.long_term import LongTermMemory
from nico.memory.manager import MemoryManager
from nico.memory.persistence import FileMemoryStore


def test_conversation_save_and_from_store() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "conv.json"
        store = FileMemoryStore(path)

        conv = ConversationMemory(store=store)
        conv.add_message("user", "hello")
        conv.add_message("assistant", "hi there")

        loaded = ConversationMemory.from_store(FileMemoryStore(path))
        assert len(loaded.messages) == 2
        assert loaded.messages[0]["role"] == "user"
        assert loaded.messages[0]["content"] == "hello"


def test_long_term_save_and_from_store() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "lt.json"
        store = FileMemoryStore(path)

        lt = LongTermMemory(store=store)
        lt.remember("name", "Alice", importance=0.9, tags=["identity"])
        lt.remember("city", "Paris")

        loaded = LongTermMemory.from_store(FileMemoryStore(path))
        assert loaded.recall("name") == "Alice"
        assert loaded.recall("city") == "Paris"


def test_memory_manager_save() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        conv_path = Path(tmp) / "conv.json"
        lt_path = Path(tmp) / "lt.json"

        mm = MemoryManager(
            conversation_store=FileMemoryStore(conv_path),
            long_term_store=FileMemoryStore(lt_path),
        )
        mm.add_turn("user", "hello")
        mm.remember("theme", "dark")

        mm.save()

        reloaded = MemoryManager.from_stores(
            conversation_store=FileMemoryStore(conv_path),
            long_term_store=FileMemoryStore(lt_path),
        )
        assert len(reloaded.conversation.messages) == 1
        assert reloaded.conversation.messages[0]["content"] == "hello"
        assert reloaded.recall("theme") == "dark"


def test_memory_manager_attach_stores() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        conv_path = Path(tmp) / "conv.json"
        lt_path = Path(tmp) / "lt.json"

        mm = MemoryManager()
        mm.attach_stores(
            conversation_store=FileMemoryStore(conv_path),
            long_term_store=FileMemoryStore(lt_path),
        )
        mm.add_turn("user", "attach test")
        mm.remember("key", "value")

        mm.save()

        reloaded = MemoryManager.from_stores(
            conversation_store=FileMemoryStore(conv_path),
            long_term_store=FileMemoryStore(lt_path),
        )
        assert reloaded.recall("key") == "value"
        assert len(reloaded.conversation.messages) == 1


def test_save_is_noop_without_store() -> None:
    conv = ConversationMemory()
    conv.add_message("user", "hello")
    conv.save()

    lt = LongTermMemory()
    lt.remember("x", "y")
    lt.save()

    mm = MemoryManager()
    mm.save()
