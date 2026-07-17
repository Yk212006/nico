from __future__ import annotations

from typing import Any

from nico.integrations.google.credentials import api_get, get_credentials

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class CalendarIntegration:
    """Google Calendar Integration via REST API."""

    def __init__(
        self,
        credentials_file: str | None = None,
        token_file: str | None = None,
        calendar_id: str = "primary",
    ) -> None:
        self._credentials_file = credentials_file
        self._token_file = token_file
        self.calendar_id = calendar_id

    async def list_events(self, max_results: int = 5, query: str | None = None) -> dict[str, Any]:
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Calendar is not configured. Set GOOGLE_CREDENTIALS_FILE to enable.", "events": []}

        try:
            params = {
                "calendarId": self.calendar_id,
                "maxResults": max_results,
                "singleEvents": "true",
                "orderBy": "startTime",
            }
            if query:
                params["q"] = query

            data = await api_get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                creds,
                params=params,
            )

            events = []
            for event in data.get("items", []):
                start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
                events.append({
                    "summary": event.get("summary", "No Title"),
                    "start": start,
                    "location": event.get("location", ""),
                    "description": event.get("description", ""),
                })
            return {"status": "ok", "events": events, "source": "Google Calendar"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "events": []}
