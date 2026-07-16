from __future__ import annotations

from typing import Any

from nico.app import NicoApp


class ClassroomTool:
    """Access Google Classroom — list courses, coursework, and submissions.

    Falls back gracefully when Google API libraries or credentials are missing.
    """

    name = "classroom"
    description = "Access Google Classroom: list courses, coursework, submissions"
    category = "integration"
    timeout_seconds = 30.0
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Action: 'list_courses' (default), 'list_coursework', 'list_submissions'",
                "default": "list_courses",
            },
            "course_id": {
                "type": "string",
                "description": "Google Classroom course ID (required for coursework/submissions)",
                "default": "",
            },
            "coursework_id": {
                "type": "string",
                "description": "Coursework ID (required for submissions)",
                "default": "",
            },
        },
    }

    def __init__(self, app: NicoApp | None = None) -> None:
        self._app = app

    async def execute(self, command: str = "list_courses", **kwargs: Any) -> str:
        if self._app is None or self._app.google_dispatcher is None:
            return "Classroom is not available (no dispatcher configured)."

        result = await self._app.google_dispatcher.handle("classroom", command=command, **kwargs)

        if result.get("status") == "unavailable":
            return f"Classroom unavailable: {result.get('message', 'not configured')}"
        if result.get("status") == "error":
            return f"Classroom error: {result.get('error', 'unknown')}"

        if command == "list_courses":
            courses = result.get("courses", [])
            if not courses:
                return "No courses found."
            lines = [f"  {c['name']} ({c['id']}) — {c.get('section', '')}" for c in courses]
            return f"Courses:\n" + "\n".join(lines)

        if command == "list_coursework":
            items = result.get("coursework", [])
            if not items:
                return "No coursework found."
            lines = []
            for cw in items:
                due = ""
                if cw.get("due_date"):
                    d = cw["due_date"]
                    due = f" due {d.get('year')}-{d.get('month'):02d}-{d.get('day'):02d}"
                lines.append(f"  {cw['title']} ({cw['id']}){due} — {cw.get('max_points', 'no points')} pts")
            return f"Coursework:\n" + "\n".join(lines)

        if command == "list_submissions":
            subs = result.get("submissions", [])
            if not subs:
                return "No submissions found."
            lines = [
                f"  Submission {s['id']} — state: {s.get('state', '')}, "
                f"grade: {s.get('assigned_grade', 'ungraded')}, late: {s.get('late', False)}"
                for s in subs
            ]
            return f"Submissions:\n" + "\n".join(lines)

        return f"Unknown classroom command: {command}"
