from __future__ import annotations

from nico.tools.camera.camera import CameraTool
from nico.tools.display.display_tool import DisplayTool
from nico.tools.files.files import FilesTool
from nico.tools.gpio.gpio import GpioTool
from nico.tools.manager import ToolManager
from nico.tools.sensors.sensor_tool import SensorTool
from nico.tools.system.system_info import SystemInfoTool
from nico.tools.vision.describe_image import DescribeImageTool


def build_tool_manager(router=None, app=None) -> ToolManager:
    """Build the offline/local tool manager."""

    manager = ToolManager()
    for tool in (
        SystemInfoTool(),
        GpioTool(),
        FilesTool(),
        CameraTool(),
    ):
        manager.register(tool)

    if router is not None:
        manager.register(DescribeImageTool(router=router))
    manager.register(DisplayTool())
    manager.register(SensorTool())

    return manager
