from __future__ import annotations

from typing import Any

from nico.integrations.google.credentials import api_get, api_post, get_credentials

SCOPES = ["https://www.googleapis.com/auth/tasks"]


class TasksIntegration:
    """Google Tasks Integration via REST API."""

    def __init__(
        self,
        credentials_file: str | None = None,
        token_file: str | None = None,
        tasklist_id: str = "@default",
    ) -> None:
        self._credentials_file = credentials_file
        self._token_file = token_file
        self.tasklist_id = tasklist_id

    async def list_tasks(self) -> dict[str, Any]:
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Tasks is not configured. Set GOOGLE_CREDENTIALS_FILE to enable.", "tasks": []}

        try:
            data = await api_get(
                f"https://tasks.googleapis.com/tasks/v1/lists/{self.tasklist_id}/tasks",
                creds,
                params={"showCompleted": "false"},
            )

            tasks = []
            for task in data.get("items", []):
                tasks.append({
                    "id": task.get("id"),
                    "title": task.get("title", "Untitled Task"),
                    "notes": task.get("notes", ""),
                    "due": task.get("due", ""),
                    "status": task.get("status", "needsAction"),
                })
            return {"status": "ok", "tasks": tasks, "source": "Google Tasks"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "tasks": []}

    async def create_task(self, title: str, notes: str | None = None, due: str | None = None) -> dict[str, Any]:
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Tasks is not configured. Set GOOGLE_CREDENTIALS_FILE to enable."}

        try:
            body: dict[str, Any] = {"title": title}
            if notes:
                body["notes"] = notes
            if due:
                body["due"] = due

            result = await api_post(
                f"https://tasks.googleapis.com/tasks/v1/lists/{self.tasklist_id}/tasks",
                creds,
                json_body=body,
            )

            return {"status": "created", "id": result.get("id"), "title": title, "source": "Google Tasks"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
