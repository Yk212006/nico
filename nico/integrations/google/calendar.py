from __future__ import annotations

from typing import Any

from nico.integrations.google.credentials import get_credentials

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


try:
    from googleapiclient.discovery import build as _build
    _GOOGLE_API = True
except ModuleNotFoundError:
    _GOOGLE_API = False


class CalendarIntegration:
    """Google Calendar Integration service.

    Uses official Google API libraries if installed and credentials are configured,
    otherwise indicates the service is unavailable.
    """

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
        """Fetch list of calendar events."""
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Calendar is not configured. Set GOOGLE_CREDENTIALS_FILE to enable.", "events": []}

        if not _GOOGLE_API:
            return {"status": "unavailable", "message": "Google API client libraries not installed.", "events": []}

        try:
            import asyncio
            service = _build("calendar", "v3", credentials=creds)
            loop = asyncio.get_running_loop()

            def _fetch():
                events_result = service.events().list(
                    calendarId=self.calendar_id,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                    q=query
                ).execute()
                return events_result.get("items", [])

            items = await loop.run_in_executor(None, _fetch)
            events = []
            for event in items:
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
