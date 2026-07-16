import pytest

from nico.memory.conversation import ConversationMemory


def test_score_importance_question() -> None:
    assert ConversationMemory.score_importance("user", "What is this?") == 0.7


def test_score_importance_short_assistant() -> None:
    assert ConversationMemory.score_importance("assistant", "Yes") == 0.3


def test_score_importance_default() -> None:
    assert ConversationMemory.score_importance("user", "hello world") == 0.5


def test_messages_stripped_for_provider_history() -> None:
    mem = ConversationMemory()
    mem.add_message("user", "hi", importance=0.9)
    mem.add_message("assistant", "hello", importance=0.5)

    history = mem.to_provider_history()
    assert len(history) == 2
    # Importance should not be in provider history
    for msg in history:
        assert "importance" not in msg


def test_summary_returns_text() -> None:
    mem = ConversationMemory()
    mem.add_message("user", "hello")
    summary = mem.summary()
    assert "user: hello" in summary


def test_auto_summarize_triggers_at_limit() -> None:
    mem = ConversationMemory(max_chars=50)
    for i in range(20):
        mem.add_message("user", f"message number {i} with some extra padding text")
    # After exceeding max_chars, messages should be pruned
    assert len(mem.messages) < 20
    assert mem._summary != ""


def test_messages_ordered_by_recency() -> None:
    mem = ConversationMemory()
    mem.add_message("user", "first")
    mem.add_message("user", "second")
    mem.add_message("user", "third")
    recent = mem.recent_messages(2)
    assert len(recent) == 2
    assert recent[0]["content"] == "second"
    assert recent[1]["content"] == "third"


def test_clear_removes_all() -> None:
    mem = ConversationMemory()
    mem.add_message("user", "test")
    mem.clear()
    assert len(mem.messages) == 0
    assert mem._summary == ""
