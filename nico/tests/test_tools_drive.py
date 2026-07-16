import pytest

from nico.tools.drive.drive_tool import DriveTool


@pytest.mark.asyncio
async def test_drive_tool_no_app_returns_unavailable():
    tool = DriveTool()
    result = await tool.execute()
    assert "not available" in result.lower()


@pytest.mark.asyncio
async def test_drive_tool_list_no_dispatcher():
    tool = DriveTool(app=None)
    result = await tool.execute(command="list")
    assert "not available" in result.lower()


def test_drive_tool_metadata():
    tool = DriveTool()
    assert tool.name == "drive"
    assert tool.category == "integration"
    assert "command" in tool.parameters["properties"]
