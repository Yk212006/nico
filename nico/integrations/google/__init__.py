from __future__ import annotations

from nico.integrations.google.calendar import CalendarIntegration
from nico.integrations.google.classroom import ClassroomIntegration
from nico.integrations.google.drive import DriveIntegration
from nico.integrations.google.gmail import GmailIntegration
from nico.integrations.google.home import HomeIntegration
from nico.integrations.google.tasks import TasksIntegration
from nico.integrations.google.credentials import get_credentials
from nico.integrations.google.dispatcher import GoogleServiceDispatcher

__all__ = [
    "CalendarIntegration",
    "ClassroomIntegration",
    "DriveIntegration",
    "GmailIntegration",
    "HomeIntegration",
    "TasksIntegration",
    "get_credentials",
    "GoogleServiceDispatcher",
]
