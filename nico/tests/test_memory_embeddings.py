import pytest

from nico.memory.embeddings import (
    OpenAIEmbeddingProvider,
    EmbeddingCache,
    cosine_similarity,
)


def test_cosine_similarity_identical() -> None:
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal() -> None:
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector() -> None:
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_stub_embeddings_are_deterministic() -> None:
    provider = OpenAIEmbeddingProvider(api_key=None)
    emb1 = provider._stub_embeddings(["hello"])
    emb2 = provider._stub_embeddings(["hello"])
    assert emb1 == emb2


def test_embed_without_key_returns_stub() -> None:
    provider = OpenAIEmbeddingProvider(api_key=None)
    import asyncio
    result = asyncio.run(provider.embed("test"))
    assert len(result) == 128
    assert all(isinstance(v, float) for v in result)


def test_embed_many_without_key_returns_stubs() -> None:
    provider = OpenAIEmbeddingProvider(api_key=None)
    import asyncio
    results = asyncio.run(provider.embed_many(["a", "b", "c"]))
    assert len(results) == 3
    assert all(len(v) == 128 for v in results)


def test_embedding_cache_set_and_get(tmp_path) -> None:
    cache = EmbeddingCache(cache_path=tmp_path / "cache.json")
    cache.set("hello", [0.1, 0.2, 0.3])
    assert cache.get("hello") == [0.1, 0.2, 0.3]


def test_embedding_cache_miss(tmp_path) -> None:
    cache = EmbeddingCache(cache_path=tmp_path / "cache.json")
    assert cache.get("nonexistent") is None


def test_embedding_cache_persists(tmp_path) -> None:
    path = tmp_path / "cache.json"
    cache1 = EmbeddingCache(cache_path=path)
    cache1.set("test", [0.5, 0.6])

    cache2 = EmbeddingCache(cache_path=path)
    assert cache2.get("test") == [0.5, 0.6]


def test_embedding_cache_clear(tmp_path) -> None:
    cache = EmbeddingCache(cache_path=tmp_path / "cache.json")
    cache.set("x", [1.0])
    cache.clear()
    assert cache.get("x") is None
