from __future__ import annotations

from typing import Any


class GpioTool:
    """Safe GPIO control tool for Raspberry Pi.

    Real GPIO operations are performed via the ``RPi.GPIO`` library when
    available.  On non-Pi systems the tool simulates the operations and
    logs what *would* have happened, so the assistant can be tested on
    any platform without hardware.

    All write operations require ``confirmed=True`` to prevent accidental
    pin state changes.
    """

    name = "gpio"
    description = "Read or write Raspberry Pi GPIO pins safely"
    category = "hardware"
    timeout_seconds = 5.0
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "pin": {
                "type": "integer",
                "description": "BCM GPIO pin number (e.g. 17, 27, 22)",
            },
            "action": {
                "type": "string",
                "enum": ["read", "set_high", "set_low", "toggle"],
                "description": "Operation to perform on the pin",
            },
            "confirmed": {
                "type": "boolean",
                "description": "Must be true to execute write operations",
            },
        },
        "required": ["pin", "action"],
    }

    def __init__(self) -> None:
        self._gpio_available = self._detect_gpio()

    @staticmethod
    def _detect_gpio() -> bool:
        try:
            import RPi.GPIO  # noqa: F401
            return True
        except (ImportError, RuntimeError):
            return False

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        pin = kwargs.get("pin")
        action = str(kwargs.get("action", "read"))
        confirmed = bool(kwargs.get("confirmed", False))

        if pin is None:
            return {"error": "Pin number is required"}

        pin_num = int(pin)

        # Read operations do not require confirmation
        is_write = action in ("set_high", "set_low", "toggle")
        if is_write and not confirmed:
            return {
                "status": "requires_confirmation",
                "pin": pin_num,
                "action": action,
                "message": (
                    f"GPIO pin {pin_num} write operation requires confirmation. "
                    "Please confirm you want to proceed."
                ),
            }

        if self._gpio_available:
            return self._real_gpio(pin_num, action)
        return self._simulated_gpio(pin_num, action)

    def _real_gpio(self, pin: int, action: str) -> dict[str, Any]:
        """Execute a real GPIO operation via RPi.GPIO."""
        try:
            import RPi.GPIO as GPIO  # noqa: PLC0415
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            if action == "read":
                GPIO.setup(pin, GPIO.IN)
                value = GPIO.input(pin)
                return {"status": "ok", "pin": pin, "action": "read", "value": value}
            if action == "set_high":
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.HIGH)
                return {"status": "executed", "pin": pin, "action": "set_high", "value": 1}
            if action == "set_low":
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
                return {"status": "executed", "pin": pin, "action": "set_low", "value": 0}
            if action == "toggle":
                GPIO.setup(pin, GPIO.OUT)
                current = GPIO.input(pin)
                GPIO.output(pin, not current)
                return {
                    "status": "executed",
                    "pin": pin,
                    "action": "toggle",
                    "value": int(not current),
                }
        except Exception as exc:
            return {"error": str(exc), "pin": pin, "action": action}

        return {"error": f"Unknown action: {action}"}

    @staticmethod
    def _simulated_gpio(pin: int, action: str) -> dict[str, Any]:
        """Simulate GPIO on non-Pi platforms for testing."""
        return {
            "status": "simulated",
            "pin": pin,
            "action": action,
            "message": (
                "GPIO simulation — RPi.GPIO not available on this platform. "
                "On a Raspberry Pi this would have executed the real operation."
            ),
        }
