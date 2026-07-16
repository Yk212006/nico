from __future__ import annotations

import logging
from typing import Any

_logger = logging.getLogger("nico.notifications")

try:
    from plyer import notification
    _PLYER = True
except ModuleNotFoundError:
    _PLYER = False


class NotificationService:
    """Delivers user-facing notifications.

    Supports:
    - Desktop notifications (via ``plyer`` if installed)
    - Voice notifications (forwarded to TTS speech synthesizer)
    - Fallback logging to stdout/stderr
    """

    def __init__(self, tts_service: Any | None = None) -> None:
        self.tts_service = tts_service

    async def send(
        self,
        title: str,
        message: str,
        *,
        desktop: bool = True,
        voice: bool = False,
    ) -> dict[str, Any]:
        """Send a notification.

        Args:
            title:   Header or subject of the notification.
            message: Body/text content.
            desktop: Deliver desktop toast notification (default true).
            voice:   Deliver vocal message if TTS is set up.

        Returns:
            Dictionary detailing dispatch status.
        """
        status: dict[str, Any] = {
            "title": title,
            "message": message,
            "desktop_sent": False,
            "voice_sent": False,
        }

        # 1. Desktop notification
        if desktop:
            if _PLYER:
                try:
                    # Run in executor to avoid blocking if the OS call takes time
                    import asyncio
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: notification.notify(
                            title=title,
                            message=message,
                            app_name="NICO Assistant",
                            timeout=5
                        )
                    )
                    status["desktop_sent"] = True
                except Exception as exc:
                    _logger.warning("Failed to send desktop notification: %s", exc)
            else:
                _logger.info("[SIMULATED TOAST] %s: %s", title, message)
                status["desktop_sent"] = "simulated"

        # 2. Voice notification
        if voice and self.tts_service:
            try:
                await self.tts_service.synthesize(f"Notification: {title}. {message}")
                status["voice_sent"] = True
            except Exception as exc:
                _logger.warning("Failed to speak notification: %s", exc)

        _logger.info("Notification sent title='%s'", title)
        return status
