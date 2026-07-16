import pytest

from nico.orchestrator import IntentOrchestrator
from nico.tools.manager import ToolManager


class DummyTool:
    name = "weather"
    description = "Weather tool"

    async def execute(self, **kwargs):
        return {"city": kwargs.get("city", "unknown")}


@pytest.mark.asyncio
async def test_orchestrator_routes_weather_intent() -> None:
    manager = ToolManager()
    manager.register(DummyTool())
    orchestrator = IntentOrchestrator(tool_manager=manager)

    result = await orchestrator.handle("what is the weather in london")

    assert result["intent"] == "tool"
    assert result["tool_name"] == "weather"


@pytest.mark.asyncio
async def test_orchestrator_routes_display_intent() -> None:
    manager = ToolManager()
    orchestrator = IntentOrchestrator(tool_manager=manager)
    result = await orchestrator.handle("show hello on display")
    assert result["intent"] == "tool"
    assert result["tool_name"] == "display"


@pytest.mark.asyncio
async def test_orchestrator_routes_classroom_courses_intent() -> None:
    manager = ToolManager()
    orchestrator = IntentOrchestrator(tool_manager=manager)
    result = await orchestrator.handle("show my google classroom courses")
    assert result["intent"] == "tool"
    assert result["tool_name"] == "classroom"
    assert result["tool_kwargs"]["command"] == "list_courses"


@pytest.mark.asyncio
async def test_orchestrator_routes_classroom_coursework_intent() -> None:
    manager = ToolManager()
    orchestrator = IntentOrchestrator(tool_manager=manager)
    result = await orchestrator.handle("list coursework for my class")
    assert result["intent"] == "tool"
    assert result["tool_name"] == "classroom"


@pytest.mark.asyncio
async def test_orchestrator_routes_drive_list_intent() -> None:
    manager = ToolManager()
    orchestrator = IntentOrchestrator(tool_manager=manager)
    result = await orchestrator.handle("list my google drive files")
    assert result["intent"] == "tool"
    assert result["tool_name"] == "drive"


@pytest.mark.asyncio
async def test_orchestrator_routes_drive_search_intent() -> None:
    manager = ToolManager()
    orchestrator = IntentOrchestrator(tool_manager=manager)
    result = await orchestrator.handle("search for project files in drive")
    assert result["intent"] == "tool"
    assert result["tool_name"] == "drive"
    assert result["tool_kwargs"]["command"] == "search"


@pytest.mark.asyncio
async def test_orchestrator_routes_sensor_intent() -> None:
    manager = ToolManager()
    orchestrator = IntentOrchestrator(tool_manager=manager)
    result = await orchestrator.handle("what is the cpu temperature")
    assert result["intent"] == "tool"
    assert result["tool_name"] == "sensors"
