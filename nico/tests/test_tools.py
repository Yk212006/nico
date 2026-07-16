import pytest

from nico.tools.manager import ToolManager
from nico.tools.registry import ToolRegistry


class EchoTool:
    name = "echo"
    description = "Echoes a message back"

    async def execute(self, **kwargs):
        return kwargs.get("message", "")


@pytest.mark.asyncio
async def test_tool_manager_executes_registered_tool() -> None:
    manager = ToolManager()
    manager.register(EchoTool())

    result = await manager.execute("echo", message="hello")

    assert result == "hello"


def test_tool_registry_discovers_tools() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    discovered = registry.discover()

    assert discovered[0]["name"] == "echo"
