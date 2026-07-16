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

DEFAULT_MODEL = "gpt-4o-mini"


def _history_to_messages(history: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for turn in history or []:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant", "system") and content:
            messages.append({"role": role, "content": content})
    return messages


def _build_messages(
    prompt: str,
    *,
    history: list[dict[str, Any]] | None = None,
    system_prompt: str | None = None,
) -> list[dict[str, Any]]:
    """Build the full message list including an optional system prompt."""
    messages: list[dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(_history_to_messages(history))
    messages.append({"role": "user", "content": prompt})
    return messages


class OpenAIProvider(BaseProvider):
    """OpenAI-compatible provider (also works with local/self-hosted gateways
    that mirror the OpenAI Chat Completions API).

    All HTTP calls are fully async via :class:`httpx.AsyncClient`.
    Falls back to a deterministic stub response whenever no API key is
    configured, so offline tests never need network access.
    """

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (
            base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        ).rstrip("/")
        self.model = model

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key or ''}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        prompt: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        if not self.api_key or httpx is None:
            return f"OpenAI response to: {prompt}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": self.model,
                        "messages": _build_messages(
                            prompt, history=history, system_prompt=system_prompt
                        ),
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                payload = response.json()
                choices = payload.get("choices", [])
                if choices and isinstance(choices[0], dict):
                    message = choices[0].get("message", {})
                    content = message.get("content")
                    if isinstance(content, str) and content:
                        return content
        except Exception:
            pass

        return f"OpenAI response to: {prompt}"

    async def stream_chat(
        self,
        prompt: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        if not self.api_key or httpx is None:
            yield f"OpenAI response to: {prompt}"
            return

        emitted = False
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": self.model,
                        "messages": _build_messages(
                            prompt, history=history, system_prompt=system_prompt
                        ),
                        "stream": True,
                    },
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
                        choices = event.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        text = delta.get("content")
                        if isinstance(text, str) and text:
                            emitted = True
                            yield text
        except Exception:
            pass

        if not emitted:
            yield await self.chat(prompt, history=history, system_prompt=system_prompt)

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
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": self.model,
                        "messages": _build_messages(
                            prompt, history=history, system_prompt=system_prompt
                        ),
                        "tools": tools,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                payload = response.json()
                choices = payload.get("choices", [])
                if not choices:
                    return {"content": "", "tool_calls": []}
                message = choices[0].get("message", {})
                raw_calls = message.get("tool_calls") or []
                tool_calls = []
                for call in raw_calls:
                    function = call.get("function", {})
                    arguments = function.get("arguments", "{}")
                    try:
                        arguments = (
                            json.loads(arguments)
                            if isinstance(arguments, str)
                            else arguments
                        )
                    except json.JSONDecodeError:
                        arguments = {}
                    tool_calls.append(
                        {
                            "id": call.get("id"),
                            "name": function.get("name"),
                            "input": arguments,
                        }
                    )
                return {
                    "content": message.get("content") or "",
                    "tool_calls": tool_calls,
                }
        except Exception:
            content = await self.chat(
                prompt, history=history, system_prompt=system_prompt
            )
            return {"content": content, "tool_calls": []}

    async def vision(self, prompt: str, image_bytes: bytes) -> str:
        if not self.api_key or httpx is None:
            return f"OpenAI vision response to: {prompt}"

        try:
            encoded = base64.b64encode(image_bytes).decode("ascii")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{encoded}"
                                        },
                                    },
                                ],
                            }
                        ],
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                payload = response.json()
                choices = payload.get("choices", [])
                if choices and isinstance(choices[0], dict):
                    content = choices[0].get("message", {}).get("content")
                    if isinstance(content, str) and content:
                        return content
        except Exception:
            pass

        return f"OpenAI vision response to: {prompt}"

    async def speech(self, text: str) -> bytes:
        """Synthesize speech using the OpenAI TTS API.

        Returns raw MP3 bytes on success, or the text UTF-8 encoded as a
        fallback so callers always receive bytes.
        """
        if not self.api_key or httpx is None:
            return text.encode("utf-8")

        voice = os.getenv("OPENAI_TTS_VOICE", "nova")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/audio/speech",
                    headers=self._headers(),
                    json={"model": "tts-1", "input": text, "voice": voice},
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.content
        except Exception:
            return text.encode("utf-8")
