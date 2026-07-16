from __future__ import annotations

import logging
from typing import Any

_logger = logging.getLogger("nico.display")

try:
    from luma.core.interface.serial import i2c
    from luma.core.render import canvas
    from luma.oled.device import ssd1306
    _LUMA_AVAILABLE = True
except (ImportError, RuntimeError):
    _LUMA_AVAILABLE = False


class DisplayController:
    """Manages system output to OLED screens (e.g. SSD1306 128x64 I2C display).

    Integrates with luma.oled and falls back to logger display on desktop.
    """

    def __init__(self) -> None:
        self._device = None
        if _LUMA_AVAILABLE:
            try:
                # SSD1306 OLED display connected via I2C on default port 1
                serial = i2c(port=1, address=0x3C)
                self._device = ssd1306(serial)
                _logger.info("luma.oled SSD1306 display initialized.")
            except Exception as exc:
                _logger.warning("Could not initialize luma.oled hardware: %s", exc)

    async def show_message(self, message: str) -> dict[str, Any]:
        """Render a text message on the screen."""
        clean_msg = message.strip()

        # 1. Drive Pi OLED display
        if self._device is not None:
            try:
                with canvas(self._device) as draw:
                    # Draw a border and the text message
                    draw.rectangle(self._device.bounding_box, outline="white", fill="black")
                    # SSD1306 displays usually fit 4-5 lines of standard text
                    words = clean_msg.split()
                    lines = []
                    current_line = []
                    for word in words:
                        if len(" ".join(current_line + [word])) <= 16:
                            current_line.append(word)
                        else:
                            lines.append(" ".join(current_line))
                            current_line = [word]
                    if current_line:
                        lines.append(" ".join(current_line))

                    y = 8
                    for line in lines[:5]:
                        draw.text((8, y), line, fill="white")
                        y += 10

                try:
                    from nico.events import HardwareStateChanged, publish
                    await publish(
                        HardwareStateChanged(
                            component="display",
                            state={"message": clean_msg}
                        )
                    )
                except Exception:
                    pass

                return {"status": "displayed", "message": clean_msg, "source": "luma.oled"}
            except Exception as exc:
                return {"status": "error", "error": str(exc), "message": clean_msg}

        # 2. Simulated Desktop fallback
        _logger.info("[OLED DISPLAY] %s", clean_msg)
        return {
            "status": "displayed",
            "message": clean_msg,
            "source": "simulated",
        }
