from __future__ import annotations

from typing import Protocol


class LifecycleService(Protocol):
    """Protocol for services that participate in app startup and shutdown."""

    async def start(self) -> None:
        ...

    async def stop(self) -> None:
        ...


class AppLifecycle:
    """Manages startup and shutdown for application services."""

    def __init__(self, services: list[LifecycleService]) -> None:
        self._services = services
        self._running = False

    async def start(self) -> None:
        for service in self._services:
            await service.start()
        self._running = True

    async def stop(self) -> None:
        for service in reversed(self._services):
            await service.stop()
        self._running = False

    def state(self) -> str:
        return "running" if self._running else "stopped"
