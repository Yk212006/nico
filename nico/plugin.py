from __future__ import annotations

import importlib
import inspect
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nico.app import NicoApp

_logger = logging.getLogger("nico.plugin")


@dataclass
class PluginMetadata:
    name: str
    version: str = "0.1.0"
    description: str = ""


class Plugin:
    """Base class for NICO plugins.

    Subclass this and override the hooks you need::

        class MyPlugin(Plugin):
            name = "my_plugin"
            version = "1.0.0"
            description = "Adds custom tools"

            async def on_load(self, app):
                app.tool_manager.register(MyTool())

            async def on_unload(self, app):
                app.tool_manager.unregister("my_tool")
    """

    name: str = ""
    version: str = "0.1.0"
    description: str = ""

    async def on_load(self, app: NicoApp) -> None:
        """Called after the plugin is registered with the app."""

    async def on_unload(self, app: NicoApp) -> None:
        """Called when the plugin is unloaded from the app."""

    def get_tools(self) -> list[Any]:
        """Return a list of tool instances to register automatically."""
        return []

    def get_services(self) -> dict[str, Any]:
        """Return a dict of services to register in the app registry."""
        return {}

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self.name or type(self).__name__,
            version=self.version,
            description=self.description,
        )


async def load_plugin(plugin: Plugin, app: NicoApp) -> None:
    """Register a plugin: attach tools, services, and fire ``on_load``."""
    for tool in plugin.get_tools():
        app.tool_manager.register(tool)
        _logger.info("Plugin '%s' registered tool '%s'", plugin.name, tool.name)
    for name, service in plugin.get_services().items():
        app.registry.register(name, service)
        _logger.info("Plugin '%s' registered service '%s'", plugin.name, name)
    await plugin.on_load(app)
    _logger.info("Plugin '%s' loaded", plugin.name)


async def unload_plugin(plugin: Plugin, app: NicoApp) -> None:
    """Unregister a plugin and fire ``on_unload``."""
    await plugin.on_unload(app)
    _logger.info("Plugin '%s' unloaded", plugin.name)


def discover_plugins(package_path: str | Path) -> list[Plugin]:
    """Scan a package directory for Plugin subclasses and instantiate them.

    Each ``.py`` file in the directory (except ``__init__``) is imported.
    Any class that is a subclass of ``Plugin`` (but not ``Plugin`` itself)
    and is defined in that module is instantiated and collected.
    """
    root = Path(package_path)
    if not root.is_dir():
        _logger.warning("Plugin discovery path '%s' is not a directory", root)
        return []

    plugins: list[Plugin] = []
    import sys
    parent = str(root.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)

    for entry in sorted(root.iterdir()):
        if entry.suffix != ".py" or entry.name == "__init__.py":
            continue
        module_name = entry.stem
        try:
            mod = importlib.import_module(f"{root.name}.{module_name}")
        except Exception as exc:
            _logger.warning("Failed to import plugin module '%s': %s", module_name, exc)
            continue

        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, Plugin) and obj is not Plugin:
                try:
                    instance = obj()
                    plugins.append(instance)
                except Exception as exc:
                    _logger.warning(
                        "Failed to instantiate plugin %s.%s: %s",
                        module_name, obj.__name__, exc,
                    )
    return plugins
