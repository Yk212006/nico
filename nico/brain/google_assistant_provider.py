from __future__ import annotations

from typing import Any, AsyncIterator

from nico.brain.provider import BaseProvider, ProviderCapabilities
from nico.integrations.google_assistant import GoogleAssistantIntegration


class GoogleAssistantProvider(BaseProvider):
    """Provider that uses the Google Assistant SDK as the brain.

    Sends queries to the Google Assistant gRPC API, which has built-in
    web search, knowledge graph answers, and smart-home device control.
    Free for personal/hobby use on custom hardware.

    Does NOT support:
    - Tool calling (no custom function calling — Google handles its own tools)
    - Vision (the gRPC API does not accept image input)
    - Streaming (responses come as a single block)
    """

    name = "google_assistant"

    def __init__(
        self,
        integration: GoogleAssistantIntegration | None = None,
    ) -> None:
        self._integration = integration or GoogleAssistantIntegration()

    @property
    def available(self) -> bool:
        return self._integration.available

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    async def chat(
        self,
        prompt: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        if not self._integration.available:
            return "Google Assistant is not configured. Set GOOGLE_CREDENTIALS_FILE, GOOGLE_ASSISTANT_DEVICE_MODEL_ID, and GOOGLE_ASSISTANT_DEVICE_ID."

        result = await self._integration.send_command(prompt)
        if result.get("status") == "ok":
            return result.get("display_text") or result.get("transcript") or ""
        return f"Google Assistant error: {result.get('message', 'unknown')}"

    async def stream_chat(
        self,
        prompt: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield the full response (Google Assistant does not stream tokens)."""
        response = await self.chat(prompt, history=history, system_prompt=system_prompt)
        yield response

    async def chat_with_tools(
        self,
        prompt: str,
        *,
        tools: list[dict[str, Any]] | None = None,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Google Assistant handles its own tools — return text content only."""
        content = await self.chat(prompt, history=history, system_prompt=system_prompt)
        return {"content": content, "tool_calls": []}

    # ------------------------------------------------------------------
    # Unsupported
    # ------------------------------------------------------------------

    async def vision(self, prompt: str, image_bytes: bytes) -> str:
        raise NotImplementedError(
            "Google Assistant gRPC API does not support image input"
        )

    async def speech(self, text: str) -> bytes:
        """Return audio bytes from Google Assistant for the given text.

        This sends the text as a query to Google Assistant and returns
        the spoken audio response, giving you the authentic Google
        Assistant voice.
        """
        result = await self._integration.send_command(text)
        audio = result.get("audio_out")
        if audio:
            return audio
        return b""

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            chat=True,
            streaming=False,
            vision=False,
            tool_calling=False,
            structured_output=False,
        )
