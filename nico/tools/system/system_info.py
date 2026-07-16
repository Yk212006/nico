from __future__ import annotations

import os
import platform
from typing import Any

try:
    import psutil  # optional — richer metrics
    _PSUTIL = True
except ModuleNotFoundError:
    _PSUTIL = False


class SystemInfoTool:
    """Returns detailed host system information.

    Uses the stdlib ``platform`` module for basic facts and ``psutil``
    (if installed) for real-time CPU, memory, and disk metrics.
    """

    name = "system_info"
    description = "Get host OS, Python version, CPU, RAM, and disk usage"
    category = "system"
    timeout_seconds = 5.0
    parameters = {
        "type": "object",
        "properties": {
            "include_hardware": {
                "type": "boolean",
                "description": "Include CPU/RAM/disk stats (default true)",
            }
        },
    }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        include_hardware: bool = bool(kwargs.get("include_hardware", True))

        info: dict[str, Any] = {
            "os": platform.system(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "processor": platform.processor() or "unknown",
        }

        # Raspberry Pi detection
        info["is_raspberry_pi"] = (
            "arm" in platform.machine().lower()
            or "aarch64" in platform.machine().lower()
        )

        if include_hardware:
            if _PSUTIL:
                import psutil  # noqa: PLC0415
                info["cpu_count"] = psutil.cpu_count(logical=True)
                info["cpu_usage_percent"] = psutil.cpu_percent(interval=0.1)
                vm = psutil.virtual_memory()
                info["ram_total_mb"] = round(vm.total / 1024 / 1024, 1)
                info["ram_used_mb"] = round(vm.used / 1024 / 1024, 1)
                info["ram_percent"] = vm.percent
                disk = psutil.disk_usage("/")
                info["disk_total_gb"] = round(disk.total / 1024 / 1024 / 1024, 1)
                info["disk_used_gb"] = round(disk.used / 1024 / 1024 / 1024, 1)
                info["disk_percent"] = disk.percent
            else:
                # Fall back to basic introspection
                info["cpu_count"] = os.cpu_count() or 1
                info["psutil_available"] = False

        # Raspberry Pi CPU temperature (Linux /sys path)
        temp_path = "/sys/class/thermal/thermal_zone0/temp"
        if os.path.exists(temp_path):
            try:
                raw = int(open(temp_path).read().strip())
                info["cpu_temp_c"] = round(raw / 1000.0, 1)
            except Exception:
                pass

        return info
