import pytest

from nico.tools.google_home.google_home import GoogleHomeTool


@pytest.mark.asyncio
async def test_google_home_requires_confirmation() -> None:
    tool = GoogleHomeTool()
    result = await tool.execute(action="turn_on", device="living_room")
    assert result["status"] == "requires_confirmation"


@pytest.mark.asyncio
async def test_google_home_unknown_action() -> None:
    tool = GoogleHomeTool()
    result = await tool.execute(action="unknown", device="test", confirmed=True)
    assert "error" in result


@pytest.mark.asyncio
async def test_google_home_simulated_with_confirmation() -> None:
    tool = GoogleHomeTool()
    result = await tool.execute(action="turn_on", device="living_room", confirmed=True)
    assert result["status"] in ("turned_on", "unavailable", "error")
