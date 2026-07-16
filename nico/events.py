"""Internal event bus for the NICO assistant.

Modules communicate through typed events rather than direct imports so
individual subsystems remain loosely coupled.  Publish an event with
:func:`publish` and subscribe with :func:`subscribe`.

Example usage::

    from nico.events import publish, subscribe, WakeWordDetected

    # In the wake-word module:
    await publish(WakeWordDetected(phrase="hey nico"))

    # In any interested module:
    async def on_wake(event: WakeWordDetected):
        print("Wake word heard:", event.phrase)

    subscribe(WakeWordDetected, on_wake)
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Type, TypeVar

_logger = logging.getLogger("nico.events")

T = TypeVar("T", bound="NicoEvent")
Handler = Callable[[Any], Awaitable[None]]

_subscribers: dict[type, list[Handler]] = defaultdict(list)


# ---------------------------------------------------------------------------
# Base event
# ---------------------------------------------------------------------------

@dataclass
class NicoEvent:
    """Base class for all NICO events."""
    pass


# ---------------------------------------------------------------------------
# Typed events
# ---------------------------------------------------------------------------

@dataclass
class WakeWordDetected(NicoEvent):
    """Fired when the wake-word detector hears the trigger phrase."""
    phrase: str = ""
    confidence: float = 1.0


@dataclass
class ConversationStarted(NicoEvent):
    """Fired at the beginning of a new conversational turn."""
    session_id: str = ""


@dataclass
class ConversationEnded(NicoEvent):
    """Fired when a conversational turn completes."""
    session_id: str = ""
    turn_count: int = 0


@dataclass
class ProviderChanged(NicoEvent):
    """Fired when the active AI provider changes."""
    from_provider: str = ""
    to_provider: str = ""


@dataclass
class ToolExecuted(NicoEvent):
    """Fired after a tool completes execution."""
    tool_name: str = ""
    success: bool = True
    duration_ms: float = 0.0
    result_summary: str = ""


@dataclass
class MemoryStored(NicoEvent):
    """Fired when a new fact or memory is persisted."""
    key: str = ""
    memory_type: str = "long_term"  # "conversation" | "long_term"


@dataclass
class HardwareStateChanged(NicoEvent):
    """Fired when a hardware component changes state."""
    component: str = ""  # "led" | "display" | "sensor" | "gpio"
    state: dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorOccurred(NicoEvent):
    """Fired when a non-fatal error occurs in any module."""
    source: str = ""
    message: str = ""
    exc_type: str = ""


@dataclass
class AppStarted(NicoEvent):
    """Fired once all services are ready."""
    assistant_name: str = ""
    provider: str = ""


@dataclass
class AppStopped(NicoEvent):
    """Fired during graceful shutdown."""
    pass


# ---------------------------------------------------------------------------
# Audio / Voice events
# ---------------------------------------------------------------------------

@dataclass
class SpeechStarted(NicoEvent):
    """Fired when TTS audio playback begins."""
    text: str = ""
    provider: str = ""


@dataclass
class SpeechEnded(NicoEvent):
    """Fired when TTS audio playback finishes."""
    text: str = ""
    duration_ms: float = 0.0


@dataclass
class ListeningStarted(NicoEvent):
    """Fired when the microphone starts recording for speech."""
    pass


@dataclass
class ListeningEnded(NicoEvent):
    """Fired when the microphone stops recording."""
    transcript: str = ""


@dataclass
class VadSpeechDetected(NicoEvent):
    """Fired when VAD detects the start of speech."""
    energy: float = 0.0


@dataclass
class VadSilenceDetected(NicoEvent):
    """Fired when VAD detects silence (end of speech)."""
    silence_duration_ms: float = 0.0


@dataclass
class InterruptionDetected(NicoEvent):
    """Fired when the user interrupts NICO speech playback."""
    pass


# ---------------------------------------------------------------------------
# Bus API
# ---------------------------------------------------------------------------

def subscribe(event_type: Type[T], handler: Callable[[T], Awaitable[None]]) -> None:
    """Register an async handler for a specific event type.

    The same handler can be registered multiple times but will only be
    called once per event if registered exactly once.
    """
    _subscribers[event_type].append(handler)  # type: ignore[arg-type]


def unsubscribe(event_type: Type[T], handler: Callable[[T], Awaitable[None]]) -> None:
    """Remove a previously registered handler."""
    handlers = _subscribers.get(event_type, [])
    try:
        handlers.remove(handler)  # type: ignore[arg-type]
    except ValueError:
        pass


async def publish(event: NicoEvent) -> None:
    """Publish an event to all registered handlers.

    Handlers are called concurrently.  Exceptions inside handlers are
    logged and suppressed so one bad handler cannot break others.
    """
    handlers = _subscribers.get(type(event), [])
    if not handlers:
        return

    async def _safe_call(handler: Handler) -> None:
        try:
            await handler(event)
        except Exception as exc:
            _logger.warning(
                "event_handler_error event=%s handler=%s error=%s",
                type(event).__name__,
                getattr(handler, "__name__", repr(handler)),
                exc,
            )

    await asyncio.gather(*(_safe_call(h) for h in handlers))


def clear_all() -> None:
    """Remove all subscribers.  Useful for test teardown."""
    _subscribers.clear()
