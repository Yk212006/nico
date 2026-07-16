import tempfile
from pathlib import Path

import pytest

from nico.app import NicoApp
from nico.config.settings import Settings
from nico.plugin import Plugin, PluginMetadata, discover_plugins, load_plugin, unload_plugin
from nico.plugin_manager import PluginManager


class GreetingTool:
    name = "greet"
    description = "Says hello"
    async def execute(self, name: str = "world") -> str:
        return f"Hello, {name}!"


class GoodbyeTool:
    name = "goodbye"
    description = "Says goodbye"
    async def execute(self) -> str:
        return "Goodbye!"


class SamplePlugin(Plugin):
    name = "sample"
    version = "1.0.0"
    description = "A test plugin"

    loaded = False
    unloaded = False

    def get_tools(self):
        return [GreetingTool()]

    def get_services(self):
        return {"sample_data": "abc"}

    async def on_load(self, app):
        SamplePlugin.loaded = True

    async def on_unload(self, app):
        SamplePlugin.unloaded = True


@pytest.fixture
def app():
    return NicoApp(settings=Settings(default_provider="openai"))


@pytest.mark.asyncio
async def test_plugin_loads_tools(app):
    plugin = SamplePlugin()
    await load_plugin(plugin, app)

    tools = app.tool_manager.list_tools()
    names = [t.name for t in tools]
    assert "greet" in names


@pytest.mark.asyncio
async def test_plugin_loads_services(app):
    plugin = SamplePlugin()
    await load_plugin(plugin, app)

    data = app.registry.resolve("sample_data")
    assert data == "abc"


@pytest.mark.asyncio
async def test_plugin_on_load_hook(app):
    SamplePlugin.loaded = False
    plugin = SamplePlugin()
    await load_plugin(plugin, app)
    assert SamplePlugin.loaded


@pytest.mark.asyncio
async def test_plugin_on_unload_hook(app):
    SamplePlugin.unloaded = False
    plugin = SamplePlugin()
    await load_plugin(plugin, app)
    await unload_plugin(plugin, app)
    assert SamplePlugin.unloaded


@pytest.mark.asyncio
async def test_plugin_manager_register(app):
    pm = PluginManager(app)
    plugin = SamplePlugin()
    await pm.register(plugin)

    names = [p.name for p in pm.list_plugins()]
    assert "sample" in names
    assert pm.get_plugin("sample") is plugin


@pytest.mark.asyncio
async def test_plugin_manager_unregister(app):
    pm = PluginManager(app)
    await pm.register(SamplePlugin())
    await pm.unregister("sample")

    assert len(pm.list_plugins()) == 0
    assert pm.get_plugin("sample") is None


@pytest.mark.asyncio
async def test_plugin_manager_duplicate_skipped(app):
    pm = PluginManager(app)
    await pm.register(SamplePlugin())
    await pm.register(SamplePlugin())

    assert len(pm.list_plugins()) == 1


@pytest.mark.asyncio
async def test_plugin_manager_unload_all(app):
    pm = PluginManager(app)

    class P1(Plugin):
        name = "p1"
    class P2(Plugin):
        name = "p2"

    await pm.register(P1())
    await pm.register(P2())
    assert len(pm.list_plugins()) == 2

    await pm.unload_all()
    assert len(pm.list_plugins()) == 0


def test_plugin_discover_empty_directory():
    with tempfile.TemporaryDirectory() as tmp:
        plugins = discover_plugins(tmp)
        assert plugins == []


def test_plugin_discover_ignores_non_py_files():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "data.txt").write_text("hello")
        plugins = discover_plugins(tmp)
        assert plugins == []


@pytest.mark.asyncio
async def test_plugin_can_register_tool_via_manager(app):
    pm = PluginManager(app)
    plugin = SamplePlugin()
    await pm.register(plugin)

    result = await app.tool_manager.execute("greet", name="NICO")
    assert result == "Hello, NICO!"


@pytest.mark.asyncio
async def test_plugin_metadata():
    plugin = SamplePlugin()
    meta = plugin.metadata()
    assert meta.name == "sample"
    assert meta.version == "1.0.0"
    assert meta.description == "A test plugin"


def test_plugin_default_metadata():
    class DefaultPlugin(Plugin):
        pass

    plugin = DefaultPlugin()
    meta = plugin.metadata()
    assert meta.name == "DefaultPlugin"
    assert meta.version == "0.1.0"
    assert meta.description == ""


@pytest.mark.asyncio
async def test_plugin_can_subscribe_to_events(app):
    from nico.events import ConversationStarted, publish, subscribe

    received = []

    async def handler(event):
        received.append(event)

    plugin = SamplePlugin()

    class EventPlugin(Plugin):
        name = "event_plugin"
        async def on_load(self, app):
            subscribe(ConversationStarted, handler)

    await load_plugin(EventPlugin(), app)
    await publish(ConversationStarted())

    assert len(received) == 1
