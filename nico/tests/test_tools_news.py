import pytest

from nico.tools.news.news import NewsTool


@pytest.mark.asyncio
async def test_news_offline(monkeypatch) -> None:
    monkeypatch.setattr("nico.tools.news.news.httpx", None)
    tool = NewsTool()
    result = await tool.execute(count=3)
    assert result["source"] == "offline"
    assert len(result["headlines"]) <= 3


@pytest.mark.asyncio
async def test_news_default_count(monkeypatch) -> None:
    monkeypatch.setattr("nico.tools.news.news.httpx", None)
    tool = NewsTool()
    result = await tool.execute()
    assert "headlines" in result


@pytest.mark.asyncio
async def test_news_max_count_ten(monkeypatch) -> None:
    monkeypatch.setattr("nico.tools.news.news.httpx", None)
    tool = NewsTool()
    result = await tool.execute(count=20)
    assert result["source"] == "offline"
    assert len(result["headlines"]) <= 10
