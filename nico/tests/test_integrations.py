import pytest

from nico.integrations.google.calendar import CalendarIntegration
from nico.integrations.google.classroom import ClassroomIntegration
from nico.integrations.google.gmail import GmailIntegration
from nico.integrations.google.home import HomeIntegration
from nico.integrations.google.tasks import TasksIntegration
from nico.integrations.google.drive import DriveIntegration


@pytest.mark.asyncio
async def test_calendar_integration_lists_events() -> None:
    integration = CalendarIntegration()
    result = await integration.list_events()
    assert "events" in result


@pytest.mark.asyncio
async def test_gmail_integration_lists_messages() -> None:
    integration = GmailIntegration()
    result = await integration.list_messages()
    assert "messages" in result


@pytest.mark.asyncio
async def test_home_integration_turns_on_light() -> None:
    integration = HomeIntegration()
    result = await integration.turn_on_light("living_room")
    assert result["device"] == "living_room"


@pytest.mark.asyncio
async def test_tasks_integration_lists_tasks() -> None:
    integration = TasksIntegration()
    result = await integration.list_tasks()
    assert "tasks" in result


@pytest.mark.asyncio
async def test_drive_integration_lists_files() -> None:
    integration = DriveIntegration()
    result = await integration.list_files()
    assert "files" in result


@pytest.mark.asyncio
async def test_drive_integration_read_file_unavailable() -> None:
    integration = DriveIntegration()
    result = await integration.read_file("some_id")
    assert result["status"] in ("unavailable", "error")


@pytest.mark.asyncio
async def test_drive_integration_get_file_info_unavailable() -> None:
    integration = DriveIntegration()
    result = await integration.get_file_info("some_id")
    assert result["status"] in ("unavailable", "error")


@pytest.mark.asyncio
async def test_drive_integration_search_files() -> None:
    integration = DriveIntegration()
    result = await integration.search_files("test")
    assert "files" in result


@pytest.mark.asyncio
async def test_classroom_integration_lists_courses() -> None:
    integration = ClassroomIntegration()
    result = await integration.list_courses()
    assert "courses" in result


@pytest.mark.asyncio
async def test_classroom_integration_lists_coursework() -> None:
    integration = ClassroomIntegration()
    result = await integration.list_coursework("some_course_id")
    assert "coursework" in result


@pytest.mark.asyncio
async def test_classroom_integration_lists_submissions() -> None:
    integration = ClassroomIntegration()
    result = await integration.list_submissions("course_id", "cw_id")
    assert "submissions" in result
