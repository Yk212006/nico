import pytest

from nico.tools.calendar.calendar_tool import CalendarTool


@pytest.mark.asyncio
async def test_calendar_offline() -> None:
    tool = CalendarTool()
    result = await tool.execute(max_results=3)
    # Without credentials, returns unavailable
    assert "status" in result
    assert "events" in result


@pytest.mark.asyncio
async def test_calendar_default_max_results() -> None:
    tool = CalendarTool()
    result = await tool.execute()
    assert "status" in result
