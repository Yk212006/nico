from __future__ import annotations

import base64
import json
import os
from typing import Any, AsyncIterator

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

from nico.brain.provider import BaseProvider

DEFAULT_MODEL = "claude-3-5-sonnet-latest"


def _history_to_messages(history: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for turn in history or []:
        role = turn.get("role")
        content = turn.get("content")
        # Claude does not accept "system" in the messages array — handled separately
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    return messages


class ClaudeProvider(BaseProvider):
    """Anthropic Claude provider.

    All HTTP calls are fully async via :class:`httpx.AsyncClient`.
    Falls back to a deterministic stub response whenever no API key is
    configured, or whenever the live request fails, so the rest of the
    application (and offline tests) never has to special-case network
    availability.
    """

    name = "claude"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = (
            base_url
            or os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
        ).rstrip("/")
        self.model = model

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key or "",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

    def _payload(
        self,
        prompt: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
        max_tokens: int = 1024,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build the request body for the Anthropic messages API."""
        body: dict[str, Any] = {
            "model": self.model,
            "messages": _history_to_messages(history) + [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        if system_prompt:
            body["system"] = system_prompt
        if extra:
            body.update(extra)
        return body

    async def chat(
        self,
        prompt: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        if not self.api_key or httpx is None:
            return f"Claude response to: {prompt}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self._headers(),
                    json=self._payload(
                        prompt,
                        history=history,
                        system_prompt=system_prompt,
                        max_tokens=1024,
                    ),
                    timeout=30.0,
                )
                response.raise_for_status()
                payload = response.json()
                content = payload.get("content", [])
                if content and isinstance(content[0], dict):
                    text = content[0].get("text")
                    if isinstance(text, str) and text:
                        return text
        except Exception:
            pass

        return f"Claude response to: {prompt}"

    async def stream_chat(
        self,
        prompt: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        if not self.api_key or httpx is None:
            yield f"Claude response to: {prompt}"
            return

        emitted = False
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/messages",
                    headers=self._headers(),
                    json=self._payload(
                        prompt,
                        history=history,
                        system_prompt=system_prompt,
                        max_tokens=1024,
                        extra={"stream": True},
                    ),
                    timeout=60.0,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        raw = line[len("data:"):].strip()
                        if raw in ("", "[DONE]"):
                            continue
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        # Claude SSE sends content_block_delta events
                        if event.get("type") == "content_block_delta":
                            delta = event.get("delta", {})
                            text = delta.get("text")
                            if isinstance(text, str) and text:
                                emitted = True
                                yield text
        except Exception:
            pass

        if not emitted:
            yield await self.chat(
                prompt, history=history, system_prompt=system_prompt
            )

    async def chat_with_tools(
        self,
        prompt: str,
        *,
        tools: list[dict[str, Any]] | None = None,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        if not self.api_key or not tools or httpx is None:
            content = await self.chat(
                prompt, history=history, system_prompt=system_prompt
            )
            return {"content": content, "tool_calls": []}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self._headers(),
                    json=self._payload(
                        prompt,
                        history=history,
                        system_prompt=system_prompt,
                        max_tokens=2048,
                        extra={"tools": tools},
                    ),
                    timeout=30.0,
                )
                response.raise_for_status()
                payload = response.json()
                blocks = payload.get("content", [])
                text_parts = [
                    b.get("text", "")
                    for b in blocks
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                tool_calls = [
                    {
                        "id": b.get("id"),
                        "name": b.get("name"),
                        "input": b.get("input", {}),
                    }
                    for b in blocks
                    if isinstance(b, dict) and b.get("type") == "tool_use"
                ]
                return {"content": "".join(text_parts), "tool_calls": tool_calls}
        except Exception:
            content = await self.chat(
                prompt, history=history, system_prompt=system_prompt
            )
            return {"content": content, "tool_calls": []}

    async def vision(self, prompt: str, image_bytes: bytes) -> str:
        if not self.api_key or httpx is None:
            return f"Claude vision response to: {prompt}"

        try:
            encoded = base64.b64encode(image_bytes).decode("ascii")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self._headers(),
                    json={
                        "model": self.model,
                        "max_tokens": 1024,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": "image/png",
                                            "data": encoded,
                                        },
                                    },
                                    {"type": "text", "text": prompt},
                                ],
                            }
                        ],
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                payload = response.json()
                content = payload.get("content", [])
                if content and isinstance(content[0], dict):
                    text = content[0].get("text")
                    if isinstance(text, str) and text:
                        return text
        except Exception:
            pass

        return f"Claude vision response to: {prompt}"

    async def speech(self, text: str) -> bytes:
        """Claude does not currently provide a TTS API — return UTF-8 bytes."""
        return text.encode("utf-8")
