from __future__ import annotations

import inspect
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from nico.brain.provider import BaseProvider
from nico.utils.logging import get_logger, log_event


def _get_supported_kwargs(func, **kwargs):
    try:
        sig = inspect.signature(func)
        # If the function accepts var keyword args (**kwargs), we can pass all kwargs
        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            return kwargs
        return {k: v for k, v in kwargs.items() if k in sig.parameters}
    except Exception:
        return kwargs



@dataclass
class RouterState:
    """Tracks the active provider and conversation history."""

    active_provider: str = "openai"
    history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ProviderHealth:
    """Tracks recent success/failure for a single provider."""

    healthy: bool = True
    consecutive_failures: int = 0
    last_error: str | None = None
    last_checked: float = field(default_factory=time.monotonic)

    def record_success(self) -> None:
        self.healthy = True
        self.consecutive_failures = 0
        self.last_error = None
        self.last_checked = time.monotonic()

    def record_failure(self, error: str, *, unhealthy_after: int = 2) -> None:
        self.consecutive_failures += 1
        self.last_error = error
        self.last_checked = time.monotonic()
        if self.consecutive_failures >= unhealthy_after:
            self.healthy = False


class ProviderRouter:
    """Routes requests across multiple providers while preserving history.

    Supports:
    - Manual routing via :meth:`select_provider` or :meth:`handle_command`
    - Automatic routing (default provider)
    - Automatic fallback: if the active provider raises or returns empty,
      the router retries remaining providers in priority order and marks
      the failing provider unhealthy so it is deprioritized (but not
      permanently excluded — it recovers after a successful call).
    - Streaming via :meth:`stream_chat`
    - Tool calling via :meth:`chat_with_tools`
    """

    def __init__(
        self,
        providers: dict[str, BaseProvider],
        default_provider: str | None = None,
        *,
        fallback_order: list[str] | None = None,
        unhealthy_after: int = 2,
    ) -> None:
        self._providers = providers
        self._state = RouterState(
            active_provider=(default_provider or "openai").lower()
        )
        self._logger = get_logger("nico.router")
        self._fallback_order = [
            p.lower() for p in (fallback_order or list(providers.keys()))
        ]
        self._health = {name: ProviderHealth() for name in providers}
        self._unhealthy_after = unhealthy_after

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> RouterState:
        return self._state

    @property
    def health(self) -> dict[str, ProviderHealth]:
        return self._health

    # ------------------------------------------------------------------
    # Provider selection
    # ------------------------------------------------------------------

    def select_provider(self, provider_name: str) -> BaseProvider:
        """Switch the active provider.  Raises ``KeyError`` for unknown names."""
        normalized = provider_name.lower()
        if normalized not in self._providers:
            raise KeyError(f"Unknown provider: {provider_name}")
        self._state.active_provider = normalized
        log_event(self._logger, "provider_selected", provider=normalized)
        return self._providers[normalized]

    def _candidate_order(self, preferred: str | None) -> list[str]:
        """Build the provider try-order: preferred first, then healthy
        providers by fallback priority, then unhealthy ones as a last resort."""
        start = (preferred or self._state.active_provider).lower()
        ordered = [start] + [p for p in self._fallback_order if p != start]
        healthy = [
            p for p in ordered if p in self._providers and self._health[p].healthy
        ]
        unhealthy = [
            p for p in ordered if p in self._providers and not self._health[p].healthy
        ]
        return healthy + unhealthy

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    async def chat(
        self,
        prompt: str,
        *,
        provider_name: str | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """Send a prompt and return the full response string.

        Automatically falls back to the next healthy provider on failure.
        """
        errors: list[str] = []
        for candidate in self._candidate_order(provider_name):
            provider = self._providers[candidate]
            try:
                call_kwargs = _get_supported_kwargs(
                    provider.chat,
                    history=self._state.history,
                    system_prompt=system_prompt,
                )
                response = await provider.chat(
                    prompt,
                    **call_kwargs
                )
            except Exception as exc:
                self._health[candidate].record_failure(
                    str(exc), unhealthy_after=self._unhealthy_after
                )
                log_event(
                    self._logger,
                    "provider_failed",
                    provider=candidate,
                    error=str(exc),
                )
                errors.append(f"{candidate}: {exc}")
                continue

            if not response:
                self._health[candidate].record_failure(
                    "empty response", unhealthy_after=self._unhealthy_after
                )
                log_event(
                    self._logger,
                    "provider_failed",
                    provider=candidate,
                    error="empty response",
                )
                errors.append(f"{candidate}: empty response")
                continue

            self._health[candidate].record_success()
            if candidate != self._state.active_provider:
                log_event(
                    self._logger,
                    "provider_fallback",
                    provider=candidate,
                    requested=provider_name,
                )
            self._state.history.append({"role": "user", "content": prompt})
            self._state.history.append({"role": "assistant", "content": response})
            return response

        raise RuntimeError(
            f"All providers failed: "
            f"{'; '.join(errors) if errors else 'no providers configured'}"
        )

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    async def stream_chat(
        self,
        prompt: str,
        *,
        provider_name: str | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream the response token-by-token with provider fallback.

        On failure the router falls back to the next healthy provider and
        yields its full (non-streamed) response so callers always receive
        at least one chunk.
        """
        accumulated: list[str] = []

        for candidate in self._candidate_order(provider_name):
            provider = self._providers[candidate]
            try:
                call_kwargs = _get_supported_kwargs(
                    provider.stream_chat,
                    history=self._state.history,
                    system_prompt=system_prompt,
                )
                async for chunk in provider.stream_chat(
                    prompt,
                    **call_kwargs
                ):
                    accumulated.append(chunk)
                    yield chunk

                if not accumulated:
                    self._health[candidate].record_failure(
                        "empty stream", unhealthy_after=self._unhealthy_after
                    )
                    continue

                self._health[candidate].record_success()
                full_response = "".join(accumulated)
                self._state.history.append({"role": "user", "content": prompt})
                self._state.history.append(
                    {"role": "assistant", "content": full_response}
                )
                return
            except Exception as exc:
                self._health[candidate].record_failure(
                    str(exc), unhealthy_after=self._unhealthy_after
                )
                log_event(
                    self._logger,
                    "provider_stream_failed",
                    provider=candidate,
                    error=str(exc),
                )
                # Reset and try next provider
                accumulated.clear()
                continue

        # All providers failed — yield a generic error message
        yield "I'm sorry, I'm unable to respond right now. Please try again later."

    # ------------------------------------------------------------------
    # Tool calling
    # ------------------------------------------------------------------

    async def chat_with_tools(
        self,
        prompt: str,
        *,
        tools: list[dict[str, Any]] | None = None,
        provider_name: str | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Route a tool-calling request to the best available provider."""
        errors: list[str] = []
        for candidate in self._candidate_order(provider_name):
            provider = self._providers[candidate]
            try:
                call_kwargs = _get_supported_kwargs(
                    provider.chat_with_tools,
                    tools=tools,
                    history=self._state.history,
                    system_prompt=system_prompt,
                )
                result = await provider.chat_with_tools(
                    prompt,
                    **call_kwargs
                )
                self._health[candidate].record_success()
                content = result.get("content", "")
                if content:
                    self._state.history.append({"role": "user", "content": prompt})
                    self._state.history.append(
                        {"role": "assistant", "content": content}
                    )
                return result
            except Exception as exc:
                self._health[candidate].record_failure(
                    str(exc), unhealthy_after=self._unhealthy_after
                )
                errors.append(f"{candidate}: {exc}")
                continue

        return {
            "content": (
                "I'm sorry, no AI provider is available right now. "
                f"Errors: {'; '.join(errors)}"
            ),
            "tool_calls": [],
        }

    # ------------------------------------------------------------------
    # Vision / Image analysis
    # ------------------------------------------------------------------

    async def vision(
        self,
        prompt: str,
        image_bytes: bytes,
        *,
        provider_name: str | None = None,
    ) -> str:
        """Analyze an image using the best available provider's vision capability.

        Falls back to the next healthy provider on failure.
        """
        errors: list[str] = []
        for candidate in self._candidate_order(provider_name):
            provider = self._providers[candidate]
            try:
                response = await provider.vision(prompt, image_bytes)
            except Exception as exc:
                self._health[candidate].record_failure(
                    str(exc), unhealthy_after=self._unhealthy_after
                )
                log_event(
                    self._logger,
                    "provider_vision_failed",
                    provider=candidate,
                    error=str(exc),
                )
                errors.append(f"{candidate}: {exc}")
                continue

            if not response:
                self._health[candidate].record_failure(
                    "empty response", unhealthy_after=self._unhealthy_after
                )
                errors.append(f"{candidate}: empty response")
                continue

            self._health[candidate].record_success()
            return response

        raise RuntimeError(
            f"All providers failed for vision request: "
            f"{'; '.join(errors) if errors else 'no providers configured'}"
        )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> dict[str, bool]:
        """Ping every provider with a trivial prompt and refresh health state."""
        results: dict[str, bool] = {}
        for name, provider in self._providers.items():
            try:
                response = await provider.chat("ping", history=[])
                ok = bool(response)
            except Exception as exc:
                ok = False
                self._health[name].record_failure(
                    str(exc), unhealthy_after=self._unhealthy_after
                )
                results[name] = ok
                continue
            if ok:
                self._health[name].record_success()
            else:
                self._health[name].record_failure(
                    "empty response", unhealthy_after=self._unhealthy_after
                )
            results[name] = ok
        return results

    # ------------------------------------------------------------------
    # Voice command handling
    # ------------------------------------------------------------------

    def handle_command(self, command: str) -> str | None:
        """Check if the message is a provider switch command.

        Returns the new provider name if a switch occurred, ``None`` otherwise.
        """
        lowered = command.strip().lower()
        if lowered.startswith("use claude") or lowered.startswith("switch to claude"):
            self.select_provider("claude")
            return "claude"
        if (
            lowered.startswith("switch to gpt")
            or lowered.startswith("use gpt")
            or lowered.startswith("use openai")
            or lowered.startswith("switch to openai")
        ):
            self.select_provider("openai")
            return "openai"
        if lowered.startswith("use gemini") or lowered.startswith("switch to gemini"):
            self.select_provider("gemini")
            return "gemini"
        return None
