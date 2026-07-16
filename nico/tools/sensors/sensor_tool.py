from __future__ import annotations

from typing import Any

from nico.hardware.sensors import SensorMonitor


class SensorTool:
    """Reads hardware sensor data including CPU temperature.

    Falls back gracefully on systems without sensor hardware.
    """

    name = "sensors"
    description = "Read hardware sensors (temperature, humidity)"
    category = "hardware"
    timeout_seconds = 10.0
    parameters = {
        "type": "object",
        "properties": {
            "sensor_type": {
                "type": "string",
                "description": "Type of sensor to read: 'temperature' (default), 'humidity', 'all'",
                "default": "temperature",
            },
        },
    }

    def __init__(self) -> None:
        self._monitor = SensorMonitor()

    async def execute(self, sensor_type: str = "temperature", **kwargs: Any) -> str:
        try:
            result = await self._monitor.read_temperature()
            temp = result.get("temperature_c", result.get("error", "unknown"))
            return f"CPU temperature: {temp}°C"
        except Exception as exc:
            return f"Sensor error: {exc}"
