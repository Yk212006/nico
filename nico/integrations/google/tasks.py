from __future__ import annotations

from typing import Any

from nico.integrations.google.credentials import get_credentials

# Scopes required for Google Tasks operations
SCOPES = ["https://www.googleapis.com/auth/tasks"]


try:
    from googleapiclient.discovery import build as _build
    _GOOGLE_API = True
except ModuleNotFoundError:
    _GOOGLE_API = False


class TasksIntegration:
    """Google Tasks Integration service.

    Supports listing tasks and creating new tasks. Uses official Google API
    libraries if configured, otherwise indicates the service is unavailable.
    """

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
        """Fetch list of tasks from the active task list."""
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Tasks is not configured. Set GOOGLE_CREDENTIALS_FILE to enable.", "tasks": []}

        if not _GOOGLE_API:
            return {"status": "unavailable", "message": "Google API client libraries not installed.", "tasks": []}

        try:
            import asyncio
            service = _build("tasks", "v1", credentials=creds)
            loop = asyncio.get_running_loop()

            def _fetch():
                results = service.tasks().list(
                    tasklist=self.tasklist_id, showCompleted=False
                ).execute()
                tasks = []
                for task in results.get("items", []):
                    tasks.append({
                        "id": task.get("id"),
                        "title": task.get("title", "Untitled Task"),
                        "notes": task.get("notes", ""),
                        "due": task.get("due", ""),
                        "status": task.get("status", "needsAction"),
                    })
                return tasks

            items = await loop.run_in_executor(None, _fetch)
            return {"status": "ok", "tasks": items, "source": "Google Tasks"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "tasks": []}

    async def create_task(self, title: str, notes: str | None = None, due: str | None = None) -> dict[str, Any]:
        """Create a new task in the active task list."""
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Tasks is not configured. Set GOOGLE_CREDENTIALS_FILE to enable."}

        if not _GOOGLE_API:
            return {"status": "unavailable", "message": "Google API client libraries not installed."}

        try:
            service = _build("tasks", "v1", credentials=creds)
            import asyncio
            loop = asyncio.get_running_loop()

            task_body = {"title": title}
            if notes:
                task_body["notes"] = notes
            if due:
                task_body["due"] = due

            def _create():
                result = service.tasks().insert(
                    tasklist=self.tasklist_id, body=task_body
                ).execute()
                return result

            result = await loop.run_in_executor(None, _create)
            return {"status": "created", "id": result.get("id"), "title": title, "source": "Google Tasks"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
