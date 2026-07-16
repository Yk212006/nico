from __future__ import annotations

from typing import Any

from nico.integrations.google.calendar import CalendarIntegration


class CalendarTool:
    """NICO tool for reading Google Calendar events via CalendarIntegration."""

    name = "calendar"
    description = "List upcoming calendar events or check your schedule"
    category = "google"
    timeout_seconds = 15.0
    parameters = {
        "type": "object",
        "properties": {
            "max_results": {
                "type": "integer",
                "description": "Maximum number of events to return (default 5)",
            },
            "query": {
                "type": "string",
                "description": "Optional search term to filter events",
            },
        },
    }

    def __init__(self, integration: CalendarIntegration | None = None) -> None:
        self._integration = integration or CalendarIntegration()

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        max_results: int = int(kwargs.get("max_results", 5))
        query: str | None = kwargs.get("query")
        return await self._integration.list_events(
            max_results=max_results, query=query
        )
