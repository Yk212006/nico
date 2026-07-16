from __future__ import annotations

import os
from typing import Any

try:
    import httpx
    _HTTPX = True
except ModuleNotFoundError:
    _HTTPX = False


class HomeIntegration:
    """Smart Home Integration service.

    Controls devices via Google Assistant SDK when configured, otherwise
    uses Home Assistant API or local simulator/stub responses.
    """

    def __init__(
        self,
        home_assistant_url: str | None = None,
        home_assistant_token: str | None = None,
    ) -> None:
        self.ha_url = home_assistant_url or os.getenv("HOME_ASSISTANT_URL", "http://homeassistant.local:8123")
        self.ha_token = home_assistant_token or os.getenv("HOME_ASSISTANT_TOKEN")
        self._assistant = _try_assistant()

    async def turn_on_light(self, device: str) -> dict[str, Any]:
        if self._assistant and self._assistant.available:
            return await self._assistant.send_command(f"turn on the {device}")
        if not self.ha_token or not _HTTPX:
            return self._stub_home_action(device, "turned_on")

        try:
            # Clean device name to HA entity ID format (e.g. light.living_room)
            entity_id = f"light.{device.replace(' ', '_').lower()}"
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ha_url.rstrip('/')}/api/services/light/turn_on",
                    headers=headers,
                    json={"entity_id": entity_id},
                    timeout=5.0,
                )
                response.raise_for_status()
                # Returns list of changed states
                return {
                    "status": "turned_on",
                    "device": entity_id,
                    "source": "Home Assistant API",
                }
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
                **self._stub_home_action(device, "turned_on"),
            }

    async def turn_off_light(self, device: str) -> dict[str, Any]:
        if self._assistant and self._assistant.available:
            return await self._assistant.send_command(f"turn off the {device}")
        if not self.ha_token or not _HTTPX:
            return self._stub_home_action(device, "turned_off")

        try:
            entity_id = f"light.{device.replace(' ', '_').lower()}"
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ha_url.rstrip('/')}/api/services/light/turn_off",
                    headers=headers,
                    json={"entity_id": entity_id},
                    timeout=5.0,
                )
                response.raise_for_status()
                return {
                    "status": "turned_off",
                    "device": entity_id,
                    "source": "Home Assistant API",
                }
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
                **self._stub_home_action(device, "turned_off"),
            }

    def _stub_home_action(self, device: str, state: str) -> dict[str, Any]:
        return {
            "status": state,
            "device": device,
            "source": "smart_home_simulator",
            "message": (
                f"Home Assistant is not configured — simulated '{state}' for device: {device}. "
                "Set HOME_ASSISTANT_TOKEN to enable real device control."
            ),
        }


def _try_assistant() -> Any | None:
    try:
        from nico.integrations.google_assistant import GoogleAssistantIntegration
        return GoogleAssistantIntegration()
    except Exception:
        return None
