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

DEFAULT_MODEL = "gemini-1.5-flash"


def _history_to_contents(history: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    for turn in history or []:
        role = turn.get("role")
        content = turn.get("content")
        if not content:
            continue
        gemini_role = "model" if role == "assistant" else "user"
        contents.append({"role": gemini_role, "parts": [{"text": content}]})
    return contents


class GeminiProvider(BaseProvider):
    """Google Gemini provider.

    All HTTP calls are fully async via :class:`httpx.AsyncClient`.
    Falls back to a deterministic stub response whenever no API key is
    configured, or whenever the live request fails.
    """

    name = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.base_url = (
            base_url
            or os.getenv(
                "GEMINI_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta",
            )
        ).rstrip("/")
        self.model = model

    def _build_body(
        self,
        prompt: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build the Gemini generateContent request body."""
        body: dict[str, Any] = {
            "contents": _history_to_contents(history)
            + [{"role": "user", "parts": [{"text": prompt}]}],
        }
        if system_prompt:
            # Gemini uses systemInstruction for system prompts
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
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
            return f"Gemini response to: {prompt}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/models/{self.model}:generateContent",
                    headers={"X-Goog-Api-Key": self.api_key},
                    json=self._build_body(
                        prompt, history=history, system_prompt=system_prompt
                    ),
                    timeout=30.0,
                )
                response.raise_for_status()
                payload = response.json()
                candidates = payload.get("candidates", [])
                if candidates and isinstance(candidates[0], dict):
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts and isinstance(parts[0], dict):
                        text = parts[0].get("text")
                        if isinstance(text, str) and text:
                            return text
        except Exception:
            pass

        return f"Gemini response to: {prompt}"

    async def stream_chat(
        self,
        prompt: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        if not self.api_key or httpx is None:
            yield f"Gemini response to: {prompt}"
            return

        emitted = False
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/models/{self.model}:streamGenerateContent"
                    f"?alt=sse",
                    headers={"X-Goog-Api-Key": self.api_key},
                    json=self._build_body(
                        prompt, history=history, system_prompt=system_prompt
                    ),
                    timeout=60.0,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        raw = line[len("data:"):].strip()
                        if not raw:
                            continue
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        candidates = event.get("candidates", [])
                        if not candidates:
                            continue
                        parts = (
                            candidates[0].get("content", {}).get("parts", [])
                        )
                        if parts and isinstance(parts[0], dict):
                            text = parts[0].get("text")
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
                    f"{self.base_url}/models/{self.model}:generateContent",
                    headers={"X-Goog-Api-Key": self.api_key},
                    json=self._build_body(
                        prompt,
                        history=history,
                        system_prompt=system_prompt,
                        extra={"tools": [{"functionDeclarations": tools}]},
                    ),
                    timeout=30.0,
                )
                response.raise_for_status()
                payload = response.json()
                candidates = payload.get("candidates", [])
                if not candidates:
                    return {"content": "", "tool_calls": []}
                parts = candidates[0].get("content", {}).get("parts", [])
                text_parts = [
                    p.get("text", "")
                    for p in parts
                    if isinstance(p, dict) and "text" in p
                ]
                tool_calls = [
                    {
                        "id": None,
                        "name": p["functionCall"].get("name"),
                        "input": p["functionCall"].get("args", {}),
                    }
                    for p in parts
                    if isinstance(p, dict) and "functionCall" in p
                ]
                return {"content": "".join(text_parts), "tool_calls": tool_calls}
        except Exception:
            content = await self.chat(
                prompt, history=history, system_prompt=system_prompt
            )
            return {"content": content, "tool_calls": []}

    async def vision(self, prompt: str, image_bytes: bytes) -> str:
        if not self.api_key or httpx is None:
            return f"Gemini vision response to: {prompt}"

        try:
            encoded = base64.b64encode(image_bytes).decode("ascii")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/models/{self.model}:generateContent",
                    headers={"X-Goog-Api-Key": self.api_key},
                    json={
                        "contents": [
                            {
                                "role": "user",
                                "parts": [
                                    {"text": prompt},
                                    {
                                        "inline_data": {
                                            "mime_type": "image/png",
                                            "data": encoded,
                                        }
                                    },
                                ],
                            }
                        ]
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                payload = response.json()
                candidates = payload.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and isinstance(parts[0], dict):
                        text = parts[0].get("text")
                        if isinstance(text, str) and text:
                            return text
        except Exception:
            pass

        return f"Gemini vision response to: {prompt}"

    async def speech(self, text: str) -> bytes:
        """Gemini does not currently provide a TTS API — return UTF-8 bytes."""
        return text.encode("utf-8")
