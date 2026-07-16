from __future__ import annotations

from typing import Any

from nico.hardware.display import DisplayController


class DisplayTool:
    """Controls an OLED display (SSD1306) to show messages.

    Falls back gracefully on systems without display hardware.
    """

    name = "display"
    description = "Show a message on the OLED display"
    category = "hardware"
    timeout_seconds = 10.0
    parameters = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Text message to display",
            },
        },
        "required": ["message"],
    }

    def __init__(self) -> None:
        self._display = DisplayController()

    async def execute(self, message: str = "", **kwargs: Any) -> str:
        try:
            result = await self._display.show_message(message)
            if result.get("status") == "error":
                return f"Display error: {result.get('error', 'unknown')}"
            return f"Display set to: {message}"
        except Exception as exc:
            return f"Display error: {exc}"
