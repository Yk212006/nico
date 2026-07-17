from __future__ import annotations

from typing import Any

from nico.integrations.google.credentials import api_get, get_credentials

SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me",
    "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly",
]


class ClassroomIntegration:
    """Google Classroom Integration via REST API."""

    def __init__(
        self,
        credentials_file: str | None = None,
        token_file: str | None = None,
    ) -> None:
        self._credentials_file = credentials_file
        self._token_file = token_file

    async def list_courses(self) -> dict[str, Any]:
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Classroom is not configured. Set GOOGLE_CREDENTIALS_FILE to enable.", "courses": []}

        try:
            data = await api_get(
                "https://classroom.googleapis.com/v1/courses",
                creds,
                params={"pageSize": 20},
            )

            courses = []
            for c in data.get("courses", []):
                courses.append({
                    "id": c.get("id"),
                    "name": c.get("name", "Untitled"),
                    "section": c.get("section", ""),
                    "description": c.get("descriptionHeading", ""),
                    "enrollment_code": c.get("enrollmentCode", ""),
                    "course_state": c.get("courseState", ""),
                })
            return {"status": "ok", "courses": courses, "source": "Google Classroom"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "courses": []}

    async def list_coursework(self, course_id: str) -> dict[str, Any]:
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Classroom is not configured.", "coursework": []}

        try:
            data = await api_get(
                f"https://classroom.googleapis.com/v1/courses/{course_id}/courseWork",
                creds,
                params={"pageSize": 20},
            )

            coursework = []
            for cw in data.get("courseWork", []):
                coursework.append({
                    "id": cw.get("id"),
                    "title": cw.get("title", "Untitled"),
                    "description": cw.get("description", ""),
                    "due_date": cw.get("dueDate", {}),
                    "due_time": cw.get("dueTime", {}),
                    "max_points": cw.get("maxPoints"),
                    "state": cw.get("state", ""),
                })
            return {"status": "ok", "coursework": coursework, "source": "Google Classroom"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "coursework": []}

    async def list_submissions(self, course_id: str, coursework_id: str) -> dict[str, Any]:
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Classroom is not configured.", "submissions": []}

        try:
            data = await api_get(
                f"https://classroom.googleapis.com/v1/courses/{course_id}/courseWork/{coursework_id}/studentSubmissions",
                creds,
                params={"pageSize": 20},
            )

            submissions = []
            for sub in data.get("studentSubmissions", []):
                submissions.append({
                    "id": sub.get("id"),
                    "user_id": sub.get("userId", ""),
                    "state": sub.get("state", ""),
                    "assigned_grade": sub.get("assignedGrade"),
                    "late": sub.get("late", False),
                    "creation_time": sub.get("creationTime", ""),
                })
            return {"status": "ok", "submissions": submissions, "source": "Google Classroom"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "submissions": []}
