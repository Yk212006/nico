import pytest

from nico.integrations.google.dispatcher import GoogleServiceDispatcher


@pytest.mark.asyncio
async def test_dispatcher_routes_calendar() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("calendar")
    assert "events" in result


@pytest.mark.asyncio
async def test_dispatcher_routes_gmail() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("gmail")
    assert "messages" in result


@pytest.mark.asyncio
async def test_dispatcher_routes_home_turn_on() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("home", device="kitchen")

    assert result["device"] == "kitchen"
    assert result["status"] == "turned_on"


@pytest.mark.asyncio
async def test_dispatcher_routes_home_turn_off() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("home", command="turn_off", device="bedroom")

    assert result["device"] == "bedroom"
    assert result["status"] == "turned_off"


@pytest.mark.asyncio
async def test_dispatcher_routes_home_unsupported_command() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("home", command="set_temperature")

    assert result["status"] == "unsupported"


@pytest.mark.asyncio
async def test_dispatcher_routes_tasks_list() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("tasks")
    assert "tasks" in result


@pytest.mark.asyncio
async def test_dispatcher_routes_tasks_create() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("tasks", command="create", title="buy milk")

    assert result["status"] == "created" or result["status"] == "unavailable"


@pytest.mark.asyncio
async def test_dispatcher_routes_drive() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("drive")
    assert "files" in result


@pytest.mark.asyncio
async def test_dispatcher_unsupported_action() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("nonexistent")

    assert result["status"] == "unsupported"


@pytest.mark.asyncio
async def test_dispatcher_tasks_unsupported_command() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("tasks", command="delete")

    assert result["status"] == "unsupported"


@pytest.mark.asyncio
async def test_dispatcher_routes_classroom_list_courses() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("classroom")
    assert "courses" in result


@pytest.mark.asyncio
async def test_dispatcher_routes_classroom_coursework() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("classroom", command="list_coursework", course_id="test123")
    assert "coursework" in result


@pytest.mark.asyncio
async def test_dispatcher_routes_classroom_submissions() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("classroom", command="list_submissions", course_id="c1", coursework_id="cw1")
    assert "submissions" in result


@pytest.mark.asyncio
async def test_dispatcher_routes_classroom_unsupported() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("classroom", command="delete_course")
    assert result["status"] == "unsupported"


@pytest.mark.asyncio
async def test_dispatcher_routes_drive_read() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("drive", command="read", file_id="test_id")
    assert "content" in result or result["status"] in ("unavailable", "error")


@pytest.mark.asyncio
async def test_dispatcher_routes_drive_info() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("drive", command="info", file_id="test_id")
    assert "file" in result or result["status"] in ("unavailable", "error")


@pytest.mark.asyncio
async def test_dispatcher_routes_drive_search() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("drive", command="search", query="test")
    assert "files" in result


@pytest.mark.asyncio
async def test_dispatcher_routes_drive_unsupported() -> None:
    dispatcher = GoogleServiceDispatcher()
    result = await dispatcher.handle("drive", command="delete")
    assert result["status"] == "unsupported"
