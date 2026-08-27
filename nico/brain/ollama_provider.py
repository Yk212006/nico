"""Ollama provider — runs AI models locally on your machine."""

from __future__ import annotations

import asyncio
import json
import os
import urllib.request
from typing import Any, AsyncIterator

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
        try:
            messages = _history_to_messages(history)
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            def _request() -> str:
                payload = json.dumps(
                    {"model": self.model, "messages": messages, "stream": False}
                ).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.base_url}/api/chat",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data.get("message", {}).get("content", "No response")

            return await asyncio.to_thread(_request)
        except Exception as exc:
            return f"Ollama error: {exc}"

    async def stream_chat(
        self,
        prompt: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        try:
            response = await self.chat(prompt, history=history, system_prompt=system_prompt)
            yield response
        except Exception as exc:
            yield f"Ollama stream error: {exc}"

    async def vision(self, prompt: str, image_bytes: bytes) -> str:
        return f"Ollama vision not yet supported. Prompt: {prompt}"

    async def speech(self, text: str) -> bytes:
        """Ollama does not provide TTS — return text as bytes."""
        return text.encode("utf-8")
