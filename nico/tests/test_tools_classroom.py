import pytest

from nico.tools.classroom.classroom_tool import ClassroomTool


@pytest.mark.asyncio
async def test_classroom_tool_no_app_returns_unavailable():
    tool = ClassroomTool()
    result = await tool.execute()
    assert "not available" in result.lower()


@pytest.mark.asyncio
async def test_classroom_tool_list_disabled():
    tool = ClassroomTool(app=None)
    result = await tool.execute(command="list_courses")
    assert "not available" in result.lower()


def test_classroom_tool_metadata():
    tool = ClassroomTool()
    assert tool.name == "classroom"
    assert tool.category == "integration"
    assert "command" in tool.parameters["properties"]
