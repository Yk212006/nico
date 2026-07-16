from __future__ import annotations

from typing import Any

from nico.integrations.google.credentials import get_credentials

SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me",
    "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly",
]

try:
    from googleapiclient.discovery import build as _build
    _GOOGLE_API = True
except ModuleNotFoundError:
    _GOOGLE_API = False


class ClassroomIntegration:
    """Google Classroom Integration service.

    Supports listing courses, coursework, and student submissions.
    Uses official Google API libraries if configured, otherwise indicates
    the service is unavailable.
    """

    def __init__(
        self,
        credentials_file: str | None = None,
        token_file: str | None = None,
    ) -> None:
        self._credentials_file = credentials_file
        self._token_file = token_file

    async def list_courses(self) -> dict[str, Any]:
        """Fetch list of enrolled courses."""
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Classroom is not configured. Set GOOGLE_CREDENTIALS_FILE to enable.", "courses": []}
        if not _GOOGLE_API:
            return {"status": "unavailable", "message": "Google API client libraries not installed.", "courses": []}
        try:
            import asyncio
            service = _build("classroom", "v1", credentials=creds)
            loop = asyncio.get_running_loop()

            def _fetch():
                results = service.courses().list(pageSize=20).execute()
                out = []
                for c in results.get("courses", []):
                    out.append({
                        "id": c.get("id"),
                        "name": c.get("name", "Untitled"),
                        "section": c.get("section", ""),
                        "description": c.get("descriptionHeading", ""),
                        "enrollment_code": c.get("enrollmentCode", ""),
                        "course_state": c.get("courseState", ""),
                    })
                return out

            items = await loop.run_in_executor(None, _fetch)
            return {"status": "ok", "courses": items, "source": "Google Classroom"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "courses": []}

    async def list_coursework(self, course_id: str) -> dict[str, Any]:
        """Fetch coursework items for a given course."""
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Classroom is not configured.", "coursework": []}
        if not _GOOGLE_API:
            return {"status": "unavailable", "message": "Google API client libraries not installed.", "coursework": []}
        try:
            import asyncio
            service = _build("classroom", "v1", credentials=creds)
            loop = asyncio.get_running_loop()

            def _fetch():
                results = service.courses().courseWork().list(
                    courseId=course_id, pageSize=20
                ).execute()
                out = []
                for cw in results.get("courseWork", []):
                    out.append({
                        "id": cw.get("id"),
                        "title": cw.get("title", "Untitled"),
                        "description": cw.get("description", ""),
                        "due_date": cw.get("dueDate", {}),
                        "due_time": cw.get("dueTime", {}),
                        "max_points": cw.get("maxPoints"),
                        "state": cw.get("state", ""),
                    })
                return out

            items = await loop.run_in_executor(None, _fetch)
            return {"status": "ok", "coursework": items, "source": "Google Classroom"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "coursework": []}

    async def list_submissions(self, course_id: str, coursework_id: str) -> dict[str, Any]:
        """Fetch student submissions for a given coursework item."""
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Classroom is not configured.", "submissions": []}
        if not _GOOGLE_API:
            return {"status": "unavailable", "message": "Google API client libraries not installed.", "submissions": []}
        try:
            import asyncio
            service = _build("classroom", "v1", credentials=creds)
            loop = asyncio.get_running_loop()

            def _fetch():
                results = service.courses().courseWork().studentSubmissions().list(
                    courseId=course_id, courseWorkId=coursework_id, pageSize=20
                ).execute()
                out = []
                for sub in results.get("studentSubmissions", []):
                    out.append({
                        "id": sub.get("id"),
                        "user_id": sub.get("userId", ""),
                        "state": sub.get("state", ""),
                        "assigned_grade": sub.get("assignedGrade"),
                        "late": sub.get("late", False),
                        "creation_time": sub.get("creationTime", ""),
                    })
                return out

            items = await loop.run_in_executor(None, _fetch)
            return {"status": "ok", "submissions": items, "source": "Google Classroom"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "submissions": []}
