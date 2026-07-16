"""Unified dispatcher for Google service integrations."""

from __future__ import annotations

from typing import Any

from nico.integrations.google.calendar import CalendarIntegration
from nico.integrations.google.classroom import ClassroomIntegration
from nico.integrations.google.drive import DriveIntegration
from nico.integrations.google.gmail import GmailIntegration
from nico.integrations.google.home import HomeIntegration
from nico.integrations.google.tasks import TasksIntegration


class GoogleServiceDispatcher:
    """Routes requests to the appropriate Google integration service.

    Provides a single ``handle()`` entry point that dispatches actions
    to Calendar, Gmail, Home, Tasks, Drive, and Classroom services.
    """

    def __init__(
        self,
        calendar: CalendarIntegration | None = None,
        gmail: GmailIntegration | None = None,
        home: HomeIntegration | None = None,
        tasks: TasksIntegration | None = None,
        drive: DriveIntegration | None = None,
        classroom: ClassroomIntegration | None = None,
    ) -> None:
        self.calendar = calendar or CalendarIntegration()
        self.gmail = gmail or GmailIntegration()
        self.home = home or HomeIntegration()
        self.tasks = tasks or TasksIntegration()
        self.drive = drive or DriveIntegration()
        self.classroom = classroom or ClassroomIntegration()

    async def handle(self, action: str, **kwargs: Any) -> dict[str, Any]:
        """Dispatch an action to the appropriate integration service.

        Args:
            action: One of ``"calendar"``, ``"gmail"``, ``"home"``,
                    ``"tasks"``, ``"drive"``, ``"classroom"``.
            **kwargs: Per-service keyword arguments forwarded directly.

        Returns:
            The integration service result dict.
        """
        if action == "calendar":
            max_results = int(kwargs.get("max_results", 5))
            query = kwargs.get("query")
            return await self.calendar.list_events(max_results=max_results, query=query)

        if action == "gmail":
            query = kwargs.get("query")
            max_results = int(kwargs.get("max_results", 5))
            return await self.gmail.list_messages(query=query, max_results=max_results)

        if action == "home":
            cmd = str(kwargs.get("command", "turn_on"))
            device = str(kwargs.get("device", "living_room"))
            if cmd == "turn_on":
                return await self.home.turn_on_light(device)
            if cmd == "turn_off":
                return await self.home.turn_off_light(device)
            return {"status": "unsupported", "command": cmd}

        if action == "tasks":
            cmd = str(kwargs.get("command", "list"))
            if cmd == "list":
                return await self.tasks.list_tasks()
            if cmd == "create":
                title = str(kwargs.get("title", ""))
                notes = kwargs.get("notes")
                due = kwargs.get("due")
                return await self.tasks.create_task(title, notes=notes, due=due)
            return {"status": "unsupported", "command": cmd}

        if action == "drive":
            cmd = str(kwargs.get("command", "list"))
            if cmd == "list":
                max_results = int(kwargs.get("max_results", 5))
                query = kwargs.get("query")
                return await self.drive.list_files(max_results=max_results, query=query)
            if cmd == "read":
                file_id = str(kwargs.get("file_id", ""))
                return await self.drive.read_file(file_id)
            if cmd == "info":
                file_id = str(kwargs.get("file_id", ""))
                return await self.drive.get_file_info(file_id)
            if cmd == "search":
                query = str(kwargs.get("query", ""))
                max_results = int(kwargs.get("max_results", 10))
                return await self.drive.search_files(query, max_results=max_results)
            return {"status": "unsupported", "command": cmd}

        if action == "classroom":
            cmd = str(kwargs.get("command", "list_courses"))
            if cmd == "list_courses":
                return await self.classroom.list_courses()
            if cmd == "list_coursework":
                course_id = str(kwargs.get("course_id", ""))
                return await self.classroom.list_coursework(course_id)
            if cmd == "list_submissions":
                course_id = str(kwargs.get("course_id", ""))
                coursework_id = str(kwargs.get("coursework_id", ""))
                return await self.classroom.list_submissions(course_id, coursework_id)
            return {"status": "unsupported", "command": cmd}

        return {"status": "unsupported", "action": action}
