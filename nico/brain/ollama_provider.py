"""Ollama provider — runs AI models locally on your machine."""

from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator

try:
    import httpx
except ModuleNotFoundError:
    httpx = None

from nico.brain.provider import BaseProvider

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"


def _history_to_messages(
    history: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    messages = []
    for turn in history or []:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if content:
            messages.append({"role": role, "content": content})
    return messages


class OllamaProvider(BaseProvider):
    """Local AI via Ollama — no API keys, no quotas, runs on your machine."""

    name = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", model)

    async def chat(
        self,
        prompt: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        if httpx is None:
            return "Ollama response (httpx not installed)"

        try:
            messages = _history_to_messages(history)
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json={"model": self.model, "messages": messages, "stream": False},
                    timeout=120.0,
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "No response")
        except Exception as exc:
            return f"Ollama error: {exc}"

    async def stream_chat(
        self,
        prompt: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        if httpx is None:
            yield "Ollama response (httpx not installed)"
            return

        try:
            messages = _history_to_messages(history)
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={"model": self.model, "messages": messages, "stream": True},
                    timeout=300.0,
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            yield f"Ollama stream error: {exc}"

    async def vision(self, prompt: str, image_bytes: bytes) -> str:
        return f"Ollama vision not yet supported. Prompt: {prompt}"

    async def speech(self, text: str) -> bytes:
        """Ollama does not provide TTS — return text as bytes."""
        return text.encode("utf-8")
