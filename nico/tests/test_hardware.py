import pytest

from nico.hardware.leds import LedController
from nico.hardware.sensors import SensorMonitor
from nico.hardware.display import DisplayController
from nico.hardware.system import SystemController


@pytest.mark.asyncio
async def test_led_controller_requires_confirmation() -> None:
    controller = LedController()
    result = await controller.set_led("green", True, confirmed=False)
    assert result["status"] == "requires_confirmation"


@pytest.mark.asyncio
async def test_sensor_monitor_reports_temperature() -> None:
    monitor = SensorMonitor()
    result = await monitor.read_temperature()
    assert "temperature_c" in result


@pytest.mark.asyncio
async def test_display_controller_sets_message() -> None:
    controller = DisplayController()
    result = await controller.show_message("Hello")
    assert result["message"] == "Hello"


@pytest.mark.asyncio
async def test_system_controller_restarts_requires_confirmation() -> None:
    controller = SystemController()
    result = await controller.restart(confirm=False)
    assert result["status"] == "requires_confirmation"
