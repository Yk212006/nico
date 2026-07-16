from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from nico.plugin import Plugin, PluginMetadata, load_plugin, unload_plugin

if TYPE_CHECKING:
    from nico.app import NicoApp

_logger = logging.getLogger("nico.plugin_manager")


class PluginManager:
    """Manages the lifecycle of plugins within a NICO application.

    Plugins can register tools, services, event handlers, and provider
    capabilities via the :class:`Plugin` interface.
    """

    def __init__(self, app: NicoApp) -> None:
        self.app = app
        self._plugins: dict[str, Plugin] = {}

    async def register(self, plugin: Plugin) -> None:
        """Register a single plugin and activate it."""
        if plugin.name in self._plugins:
            _logger.warning("Plugin '%s' already registered, skipping", plugin.name)
            return
        self._plugins[plugin.name] = plugin
        await load_plugin(plugin, self.app)

    async def unregister(self, name: str) -> None:
        """Unregister and deactivate a plugin by name."""
        plugin = self._plugins.pop(name, None)
        if plugin is not None:
            await unload_plugin(plugin, self.app)
        else:
            _logger.warning("Plugin '%s' not found, cannot unregister", name)

    async def load_from_package(self, package_path: str) -> list[PluginMetadata]:
        """Discover and register all plugins from a package directory.

        Returns metadata for each successfully loaded plugin.
        """
        from nico.plugin import discover_plugins

        discovered = discover_plugins(package_path)
        loaded: list[PluginMetadata] = []
        for plugin in discovered:
            try:
                await self.register(plugin)
                loaded.append(plugin.metadata())
            except Exception as exc:
                _logger.error(
                    "Failed to load plugin '%s': %s",
                    plugin.name or type(plugin).__name__, exc,
                )
        return loaded

    def list_plugins(self) -> list[PluginMetadata]:
        """Return metadata for all registered plugins."""
        return [p.metadata() for p in self._plugins.values()]

    def get_plugin(self, name: str) -> Plugin | None:
        """Return a registered plugin by name, or ``None``."""
        return self._plugins.get(name)

    async def unload_all(self) -> None:
        """Unregister all active plugins."""
        for name in list(self._plugins):
            await self.unregister(name)
