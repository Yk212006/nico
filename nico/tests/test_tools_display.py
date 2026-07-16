import pytest

from nico.tools.display.display_tool import DisplayTool


@pytest.mark.asyncio
async def test_display_tool_sets_message():
    tool = DisplayTool()
    result = await tool.execute(message="hello")
    assert "hello" in result


@pytest.mark.asyncio
async def test_display_tool_empty_message():
    tool = DisplayTool()
    result = await tool.execute(message="")
    assert "Display" in result


def test_display_tool_registered():
    from nico.app import NicoApp
    from nico.config.settings import Settings

    app = NicoApp(settings=Settings(default_provider="openai"))
    names = [t.name for t in app.tool_manager.list_tools()]
    assert "display" in names
