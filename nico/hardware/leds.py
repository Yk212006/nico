from __future__ import annotations

import logging
from typing import Any

_logger = logging.getLogger("nico.leds")

try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    _GPIO_AVAILABLE = False

# Mapping of colors to BCM GPIO Pin numbers on the Raspberry Pi
# Default common pins for a Tri-color (RGB) LED.
COLOR_PINS = {
    "red": 17,
    "green": 27,
    "blue": 22,
}


class LedController:
    """Controls onboard status LEDs for feedback.

    Uses RPi.GPIO on Raspberry Pi and log-based simulation on desktop.
    """

    def __init__(self) -> None:
        self._initialized = False
        if _GPIO_AVAILABLE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                for pin in COLOR_PINS.values():
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.LOW)
                self._initialized = True
            except Exception as exc:
                _logger.warning("Failed to initialize RPi.GPIO LEDs: %s", exc)

    async def set_led(self, color: str, state: bool, *, confirmed: bool = False) -> dict[str, Any]:
        """Turn an LED color pin on or off.

        Args:
            color:     "red" | "green" | "blue"
            state:     True (on) | False (off)
            confirmed: Explicit confirmation needed for modification.
        """
        color_lower = color.lower().strip()
        if color_lower not in COLOR_PINS:
            return {"status": "unsupported_color", "color": color}

        if not confirmed:
            return {
                "status": "requires_confirmation",
                "color": color_lower,
                "state": state,
            }

        # 1. Drive Pi hardware
        if self._initialized and _GPIO_AVAILABLE:
            try:
                pin = COLOR_PINS[color_lower]
                val = GPIO.HIGH if state else GPIO.LOW
                GPIO.output(pin, val)
                
                # Fire event
                try:
                    from nico.events import HardwareStateChanged, publish
                    await publish(
                        HardwareStateChanged(
                            component="led",
                            state={"color": color_lower, "active": state}
                        )
                    )
                except Exception:
                    pass

                return {"status": "executed", "color": color_lower, "state": state, "source": "RPi.GPIO"}
            except Exception as exc:
                return {"status": "error", "error": str(exc), "color": color_lower, "state": state}

        # 2. Simulated Desktop fallback
        _logger.info("[LED STATUS] color=%s active=%s", color_lower, state)
        return {
            "status": "simulated",
            "color": color_lower,
            "state": state,
            "source": "simulated",
        }
