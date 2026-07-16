from __future__ import annotations

from typing import Any

from nico.integrations.google.home import HomeIntegration


class GoogleHomeTool:
    """Controls smart home devices via Google Assistant or Home Assistant.

    Uses Google Assistant SDK when configured (GOOGLE_ASSISTANT_DEVICE_MODEL_ID
    and GOOGLE_ASSISTANT_DEVICE_ID), otherwise falls back to Home Assistant.
    """

    name = "google_home"
    description = "Control smart home devices (lights, switches, etc.)"
    category = "home"
    timeout_seconds = 10.0
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["turn_on", "turn_off"],
                "description": "Whether to turn the device on or off",
            },
            "device": {
                "type": "string",
                "description": "Device name or room (e.g. 'living_room', 'bedroom')",
            },
            "confirmed": {
                "type": "boolean",
                "description": "Must be true to execute device control",
            },
        },
        "required": ["action", "device"],
    }

    def __init__(
        self,
        integration: HomeIntegration | None = None,
        assistant_integration: Any | None = None,
    ) -> None:
        self._integration = integration or HomeIntegration()
        self._assistant = assistant_integration
        if self._assistant is None:
            try:
                from nico.integrations.google_assistant import GoogleAssistantIntegration
                self._assistant = GoogleAssistantIntegration()
            except ImportError:
                self._assistant = None

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        action = str(kwargs.get("action", "turn_on"))
        device = str(kwargs.get("device", "living_room"))
        confirmed = bool(kwargs.get("confirmed", False))

        if not confirmed:
            return {
                "status": "requires_confirmation",
                "message": f"Turning {action} '{device}' requires confirmation.",
            }

        if self._assistant and self._assistant.available:
            cmd = f"{action.replace('_', ' ')} the {device}"
            return await self._assistant.send_command(cmd)

        if action == "turn_on":
            return await self._integration.turn_on_light(device)
        if action == "turn_off":
            return await self._integration.turn_off_light(device)
        return {"error": f"Unknown action: {action}"}
