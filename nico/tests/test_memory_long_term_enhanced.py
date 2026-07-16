import pytest

from nico.memory.long_term import LongTermMemory


@pytest.fixture
def memory() -> LongTermMemory:
    return LongTermMemory()


def test_remember_and_recall(memory: LongTermMemory) -> None:
    memory.remember("color", "blue")
    assert memory.recall("color") == "blue"


def test_recall_default(memory: LongTermMemory) -> None:
    assert memory.recall("nonexistent", "fallback") == "fallback"


def test_forget(memory: LongTermMemory) -> None:
    memory.remember("key", "val")
    assert memory.forget("key") is True
    assert memory.recall("key") is None


def test_forget_nonexistent(memory: LongTermMemory) -> None:
    assert memory.forget("nope") is False


def test_update_keeps_importance(memory: LongTermMemory) -> None:
    memory.remember("x", 1, importance=0.9, tags=["test"])
    memory.update("x", 2)
    assert memory.recall("x") == 2
    search = memory.search("x")
    assert search[0]["meta"]["importance"] == 0.9
    assert "test" in search[0]["meta"]["tags"]


def test_keyword_search(memory: LongTermMemory) -> None:
    memory.remember("user_name", "Alice", tags=["identity"])
    memory.remember("city", "Paris", tags=["location"])
    memory.remember("unrelated", "foo")

    results = memory.search("alice")
    assert len(results) == 1
    assert results[0]["key"] == "user_name"

    results = memory.search("paris")
    assert len(results) == 1
    assert results[0]["key"] == "city"


def test_search_by_tag(memory: LongTermMemory) -> None:
    memory.remember("habit", "reading", tags=["preference", "hobby"])
    results = memory.search("hobby")
    assert len(results) == 1
    assert results[0]["key"] == "habit"


def test_search_importance_ordering(memory: LongTermMemory) -> None:
    memory.remember("a", "low value", importance=0.3)
    memory.remember("b", "high value", importance=0.9)
    results = memory.search("value")
    assert len(results) == 2
    assert results[0]["key"] == "b"


def test_list_facts(memory: LongTermMemory) -> None:
    memory.remember("a", 1)
    memory.remember("b", 2)
    facts = memory.list_facts()
    assert facts == {"a": 1, "b": 2}


def test_reset(memory: LongTermMemory) -> None:
    memory.remember("x", "y")
    memory.reset()
    assert memory.list_facts() == {}


def test_prune_removes_low_importance(memory: LongTermMemory) -> None:
    for i in range(10):
        memory.remember(f"k{i}", i, importance=0.1 * (i + 1))
    removed = memory.prune(keep_top_n=5)
    assert removed == 5
    facts = memory.list_facts()
    # The 5 highest-importance keys should remain
    remaining_importance = [memory._meta[k]["importance"] for k in facts]
    assert all(imp >= 0.6 for imp in remaining_importance)


def test_prune_noop_when_under_limit(memory: LongTermMemory) -> None:
    memory.remember("a", 1)
    assert memory.prune(keep_top_n=100) == 0


def test_preferences(memory: LongTermMemory) -> None:
    memory.set_preference("theme", "dark")
    memory.set_preference("language", "en")
    assert memory.get_preferences() == {"theme": "dark", "language": "en"}


def test_regular_fact_not_in_preferences(memory: LongTermMemory) -> None:
    memory.remember("temp", "data")
    assert memory.get_preferences() == {}
