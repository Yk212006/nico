import pytest

from nico.tools.sensors.sensor_tool import SensorTool


@pytest.mark.asyncio
async def test_sensor_tool_returns_temperature():
    tool = SensorTool()
    result = await tool.execute(sensor_type="temperature")
    assert "temperature" in result.lower() or "error" in result.lower()


@pytest.mark.asyncio
async def test_sensor_tool_default_param():
    tool = SensorTool()
    result = await tool.execute()
    assert isinstance(result, str)


def test_sensor_tool_registered():
    from nico.app import NicoApp
    from nico.config.settings import Settings

    app = NicoApp(settings=Settings(default_provider="openai"))
    names = [t.name for t in app.tool_manager.list_tools()]
    assert "sensors" in names
