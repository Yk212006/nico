from __future__ import annotations

from typing import Any

from nico.tools.manager import ToolManager


class ToolRegistry:
    """Registry for managing and dynamically discovering tools."""

    def __init__(self, manager: ToolManager | None = None) -> None:
        self.manager = manager or ToolManager()

    def register(self, tool: Any) -> None:
        self.manager.register(tool)

    def discover(self) -> list[dict[str, Any]]:
        """Return a simplified representation of registered tools."""
        return [
            {
                "name": metadata.name,
                "description": metadata.description,
                "category": metadata.category,
                "parameters": metadata.parameters,
                "requires_confirmation": metadata.requires_confirmation,
            }
            for metadata in self.manager.list_tools()
        ]


