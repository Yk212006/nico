from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator


@dataclass(frozen=True)
class ProviderCapabilities:
    """Capabilities a provider supports, detected automatically at runtime."""

    chat: bool = False
    streaming: bool = False
    vision: bool = False
    tool_calling: bool = False
    structured_output: bool = False

    def as_dict(self) -> dict[str, bool]:
        return {
            "chat": self.chat,
            "streaming": self.streaming,
            "vision": self.vision,
            "tool_calling": self.tool_calling,
            "structured_output": self.structured_output,
        }


class BaseProvider(ABC):
    """Abstract base class for concrete providers.

    Subclasses only need to override the methods they actually support.
    Methods left as the base "not implemented" stubs are automatically
    excluded from :meth:`capabilities`, so the rest of the app can check
    ``provider.capabilities.tool_calling`` etc. instead of hardcoding a
    per-provider feature matrix.
    """

    name: str = "base"

    @abstractmethod
    async def chat(
        self,
        prompt: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        raise NotImplementedError

    async def stream_chat(
        self,
        prompt: str,
        *,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Default streaming implementation: yield the full response once.

        Providers that support real token/SSE streaming should override
        this method; callers can still treat every provider uniformly as
        an async generator.
        """
        try:
            sig = inspect.signature(self.chat)
            kwargs = {}
            if "history" in sig.parameters:
                kwargs["history"] = history
            if "system_prompt" in sig.parameters:
                kwargs["system_prompt"] = system_prompt
            response = await self.chat(prompt, **kwargs)
        except Exception:
            response = await self.chat(prompt)
        yield response

    async def chat_with_tools(
        self,
        prompt: str,
        *,
        tools: list[dict[str, Any]] | None = None,
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Default tool-calling implementation: no tool calls are ever made."""
        try:
            sig = inspect.signature(self.chat)
            kwargs = {}
            if "history" in sig.parameters:
                kwargs["history"] = history
            if "system_prompt" in sig.parameters:
                kwargs["system_prompt"] = system_prompt
            content = await self.chat(prompt, **kwargs)
        except Exception:
            content = await self.chat(prompt)
        return {"content": content, "tool_calls": []}

    @abstractmethod
    async def vision(self, prompt: str, image_bytes: bytes) -> str:
        raise NotImplementedError

    @abstractmethod
    async def speech(self, text: str) -> bytes:
        raise NotImplementedError

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Detect which optional capabilities this provider actually supports.

        A capability is considered supported when the subclass overrides the
        corresponding method rather than relying on the base "unsupported"
        implementation.
        """

        return detect_capabilities(self)


def _is_overridden(instance: Any, method_name: str, base_cls: type) -> bool:
    bound = getattr(type(instance), method_name, None)
    base = getattr(base_cls, method_name, None)
    if bound is None or base is None:
        return False
    return inspect.unwrap(bound) is not inspect.unwrap(base)


def detect_capabilities(provider: "BaseProvider") -> ProviderCapabilities:
    """Inspect a provider instance and report which features it implements."""

    return ProviderCapabilities(
        chat=_is_overridden(provider, "chat", BaseProvider),
        streaming=_is_overridden(provider, "stream_chat", BaseProvider),
        vision=_is_overridden(provider, "vision", BaseProvider),
        tool_calling=_is_overridden(provider, "chat_with_tools", BaseProvider),
        structured_output=_is_overridden(provider, "chat_with_tools", BaseProvider),
    )
