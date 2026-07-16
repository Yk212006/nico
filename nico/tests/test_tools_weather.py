import pytest

from nico.tools.weather.weather import WeatherTool


@pytest.mark.asyncio
async def test_weather_offline_without_key() -> None:
    tool = WeatherTool(api_key=None)
    result = await tool.execute(city="London")
    assert "source" in result
    assert result.get("city") == "London"


@pytest.mark.asyncio
async def test_weather_returns_description() -> None:
    tool = WeatherTool(api_key=None)
    result = await tool.execute(city="Tokyo", units="metric")
    assert "description" in result
    assert "temperature" in result
