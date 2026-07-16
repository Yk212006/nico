from __future__ import annotations

from typing import TYPE_CHECKING

from nico.tools.gpio.gpio import GpioTool
from nico.tools.manager import ToolManager
from nico.tools.news.news import NewsTool
from nico.tools.system.system_info import SystemInfoTool
from nico.tools.weather.weather import WeatherTool
from nico.tools.files.files import FilesTool
from nico.tools.calendar.calendar_tool import CalendarTool
from nico.tools.email.email_tool import EmailTool
from nico.tools.camera.camera import CameraTool
from nico.tools.google_home.google_home import GoogleHomeTool
from nico.tools.vision.describe_image import DescribeImageTool
from nico.tools.display.display_tool import DisplayTool
from nico.tools.sensors.sensor_tool import SensorTool
from nico.tools.whatsapp.whatsapp_tool import WhatsAppTool

if TYPE_CHECKING:
    from nico.app import NicoApp
    from nico.brain.router import ProviderRouter


def build_tool_manager(router: ProviderRouter | None = None, app: NicoApp | None = None) -> ToolManager:
    """Build a tool manager with the default built-in tools.

    If a *router* is provided, the ``describe_image`` tool will be
    registered with vision capability.  If an *app* is provided,
    tools that need access to the app's dispatcher (Drive, Classroom)
    will be registered.
    """

    manager = ToolManager()
    for tool in (
        SystemInfoTool(),
        WeatherTool(),
        NewsTool(),
        GpioTool(),
        FilesTool(),
        CalendarTool(),
        EmailTool(),
        CameraTool(),
        GoogleHomeTool(),
        WhatsAppTool(),
    ):
        manager.register(tool)

    if router is not None:
        manager.register(DescribeImageTool(router=router))
    manager.register(DisplayTool())
    manager.register(SensorTool())

    if app is not None:
        from nico.tools.drive.drive_tool import DriveTool
        from nico.tools.classroom.classroom_tool import ClassroomTool
        manager.register(DriveTool(app=app))
        manager.register(ClassroomTool(app=app))

    return manager
