from __future__ import annotations

import os
import subprocess
import platform
from typing import Any


class SystemController:
    """Handles safe system-level power controls (shutdown, restart, sleep).

    Verifies confirmation parameters and requires the ``NICO_ALLOW_SYSTEM_CONTROL``
    setting to be enabled.
    """

    def __init__(self, allow_system_control: bool | None = None) -> None:
        # Default to reading environment variable directly
        env_val = os.getenv("NICO_ALLOW_SYSTEM_CONTROL", "false").lower() == "true"
        self.allow_system_control = (
            allow_system_control if allow_system_control is not None else env_val
        )

    async def shutdown(self, *, confirm: bool = False) -> dict[str, Any]:
        """Perform system shutdown."""
        if not confirm:
            return {
                "status": "requires_confirmation",
                "action": "shutdown",
                "message": "Are you sure you want to shut down NICO? Please confirm this action.",
            }

        if not self.allow_system_control:
            return {
                "status": "denied",
                "action": "shutdown",
                "message": "System power control is disabled in NICO settings.",
            }

        # Platform specific shutdown commands
        try:
            system = platform.system().lower()
            if "linux" in system or "darwin" in system:
                # Trigger shutdown asynchronously
                subprocess.Popen(["sudo", "shutdown", "-h", "now"])
            elif "windows" in system:
                subprocess.Popen(["shutdown", "/s", "/t", "0"])
            
            # Fire event before execution
            try:
                from nico.events import HardwareStateChanged, publish
                await publish(HardwareStateChanged(component="system", state={"action": "shutdown"}))
            except Exception:
                pass

            return {"status": "executed", "action": "shutdown", "message": "Shutdown command issued."}
        except Exception as exc:
            return {"status": "error", "action": "shutdown", "message": str(exc)}

    async def restart(self, *, confirm: bool = False) -> dict[str, Any]:
        """Perform system reboot."""
        if not confirm:
            return {
                "status": "requires_confirmation",
                "action": "restart",
                "message": "Are you sure you want to restart NICO? Please confirm this action.",
            }

        if not self.allow_system_control:
            return {
                "status": "denied",
                "action": "restart",
                "message": "System power control is disabled in NICO settings.",
            }

        try:
            system = platform.system().lower()
            if "linux" in system or "darwin" in system:
                subprocess.Popen(["sudo", "shutdown", "-r", "now"])
            elif "windows" in system:
                subprocess.Popen(["shutdown", "/r", "/t", "0"])
            
            try:
                from nico.events import HardwareStateChanged, publish
                await publish(HardwareStateChanged(component="system", state={"action": "restart"}))
            except Exception:
                pass

            return {"status": "executed", "action": "restart", "message": "Restart command issued."}
        except Exception as exc:
            return {"status": "error", "action": "restart", "message": str(exc)}

    async def sleep(self, *, confirm: bool = False) -> dict[str, Any]:
        """Put the device into low power sleep/suspend mode."""
        if not confirm:
            return {
                "status": "requires_confirmation",
                "action": "sleep",
                "message": "Are you sure you want to put NICO to sleep? Please confirm this action.",
            }

        if not self.allow_system_control:
            return {
                "status": "denied",
                "action": "sleep",
                "message": "System power control is disabled in NICO settings.",
            }

        try:
            system = platform.system().lower()
            if "linux" in system:
                subprocess.Popen(["sudo", "systemctl", "suspend"])
            elif "windows" in system:
                subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
            
            try:
                from nico.events import HardwareStateChanged, publish
                await publish(HardwareStateChanged(component="system", state={"action": "sleep"}))
            except Exception:
                pass

            return {"status": "executed", "action": "sleep", "message": "Sleep command issued."}
        except Exception as exc:
            return {"status": "error", "action": "sleep", "message": str(exc)}

    async def handle_action(self, action: str, *, confirm: bool = False) -> dict[str, Any]:
        action_name = action.lower().strip()
        if action_name == "shutdown":
            return await self.shutdown(confirm=confirm)
        if action_name == "restart" or action_name == "reboot":
            return await self.restart(confirm=confirm)
        if action_name == "sleep" or action_name == "suspend":
            return await self.sleep(confirm=confirm)
        return {"status": "unsupported", "action": action_name}
