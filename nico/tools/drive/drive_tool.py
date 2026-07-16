from __future__ import annotations

from typing import Any

from nico.app import NicoApp


class DriveTool:
    """Access Google Drive files — list, read content, search, and get file info.

    Falls back gracefully when Google API libraries or credentials are missing.
    """

    name = "drive"
    description = "Access Google Drive files: list, read, search, get file info"
    category = "integration"
    timeout_seconds = 30.0
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Action: 'list' (default), 'read', 'search', 'info'",
                "default": "list",
            },
            "query": {
                "type": "string",
                "description": "Search query (used with list/search commands)",
                "default": "",
            },
            "file_id": {
                "type": "string",
                "description": "Google Drive file ID (used with read/info commands)",
                "default": "",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results for list/search (default 10)",
                "default": 10,
            },
        },
    }

    def __init__(self, app: NicoApp | None = None) -> None:
        self._app = app

    async def execute(self, command: str = "list", **kwargs: Any) -> str:
        if self._app is None or self._app.google_dispatcher is None:
            return "Drive is not available (no dispatcher configured)."

        result = await self._app.google_dispatcher.handle("drive", command=command, **kwargs)

        if result.get("status") == "unavailable":
            return f"Drive unavailable: {result.get('message', 'not configured')}"
        if result.get("status") == "error":
            return f"Drive error: {result.get('error', 'unknown')}"

        if command == "list" or command == "search":
            files = result.get("files", [])
            if not files:
                return "No files found."
            lines = [f"  {f['name']} ({f['id']}) — {f.get('mime_type', '')}" for f in files]
            return f"Files:\n" + "\n".join(lines)

        if command == "read":
            content = result.get("content", "")
            meta = result.get("metadata", {})
            name = meta.get("name", "unknown")
            return f"Content of '{name}':\n{content[:2000]}"

        if command == "info":
            f = result.get("file", {})
            if not f:
                return "File not found."
            return (
                f"Name: {f['name']}\n"
                f"Type: {f.get('mime_type', '')}\n"
                f"Size: {f.get('size_bytes', 'unknown')} bytes\n"
                f"Created: {f.get('created', '')}\n"
                f"Modified: {f.get('modified', '')}\n"
                f"Web Link: {f.get('web_link', '')}"
            )

        return f"Unknown drive command: {command}"
