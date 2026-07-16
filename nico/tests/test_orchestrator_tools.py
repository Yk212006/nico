import pytest

from nico.orchestrator import IntentOrchestrator
from nico.tools.manager import ToolManager


class DummySystemTool:
    name = "system_info"
    description = "System info tool"

    async def execute(self, **kwargs):
        return {"ok": True}


@pytest.mark.asyncio
async def test_orchestrator_routes_system_info_intent() -> None:
    manager = ToolManager()
    manager.register(DummySystemTool())
    orchestrator = IntentOrchestrator(tool_manager=manager)

    result = await orchestrator.handle("tell me about the system")

    assert result["intent"] == "tool"
    assert result["tool_name"] == "system_info"
