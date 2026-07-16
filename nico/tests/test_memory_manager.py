import pytest

from nico.memory.conversation import ConversationMemory
from nico.memory.long_term import LongTermMemory
from nico.memory.manager import MemoryManager


@pytest.fixture
def manager() -> MemoryManager:
    return MemoryManager()


def test_add_turn_stores_in_conversation(manager: MemoryManager) -> None:
    manager.add_turn("user", "hello")
    assert len(manager.conversation.messages) == 1
    assert manager.conversation.messages[0]["content"] == "hello"


def test_add_turn_consolidates_name(manager: MemoryManager) -> None:
    manager.add_turn("user", "My name is Alice")
    assert manager.long_term.recall("user_name") == "Alice"


def test_add_turn_consolidates_call_me(manager: MemoryManager) -> None:
    manager.add_turn("user", "Please call me Bob")
    assert manager.long_term.recall("user_name_preferred") == "Bob"


def test_add_turn_consolidates_location(manager: MemoryManager) -> None:
    manager.add_turn("user", "I live in New York")
    assert "new york" in manager.long_term.recall("user_location").lower()


def test_assistant_turns_not_consolidated(manager: MemoryManager) -> None:
    manager.add_turn("assistant", "My name is NICO")
    assert manager.long_term.recall("user_name") is None


def test_low_importance_not_consolidated(manager: MemoryManager) -> None:
    manager.add_turn("user", "ok")
    assert manager.long_term.list_facts() == {}


def test_remember_and_recall_long_term(manager: MemoryManager) -> None:
    manager.remember("key", "value")
    assert manager.recall("key") == "value"


def test_search_long_term(manager: MemoryManager) -> None:
    manager.remember("city", "Tokyo", tags=["location"])
    results = manager.search("tokyo")
    assert len(results) >= 1


def test_preferences(manager: MemoryManager) -> None:
    manager.set_preference("mode", "quiet")
    assert manager.get_preferences() == {"mode": "quiet"}


def test_recent_history(manager: MemoryManager) -> None:
    manager.add_turn("user", "hi")
    manager.add_turn("assistant", "hello")
    history = manager.recent_history()
    assert len(history) >= 2


def test_clear_conversation(manager: MemoryManager) -> None:
    manager.add_turn("user", "hi")
    manager.clear_conversation()
    assert len(manager.conversation.messages) == 0


def test_reset_all(manager: MemoryManager) -> None:
    manager.add_turn("user", "hi")
    manager.remember("k", "v")
    manager.reset_all()
    assert len(manager.conversation.messages) == 0
    assert manager.long_term.list_facts() == {}


def test_prune_long_term(manager: MemoryManager) -> None:
    for i in range(15):
        manager.remember(f"k{i}", i, importance=0.1)
    removed = manager.prune_long_term(keep_top_n=10)
    assert removed == 5


def test_importance_scores_conversation_messages(manager: MemoryManager) -> None:
    manager.add_turn("user", "What is the weather?")
    manager.add_turn("assistant", "Yes")
    manager.add_turn("user", "Tell me more")

    assert len(manager.conversation.messages) == 3
    # Questions should have higher importance
    assert manager.conversation.messages[0]["importance"] == 0.7
    # Short assistant response should have lower importance
    assert manager.conversation.messages[1]["importance"] == 0.3
