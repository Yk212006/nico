from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T")


class ServiceRegistry:
    """Registers and resolves services by name for dependency-based assembly."""

    def __init__(self) -> None:
        self._services: dict[str, Any] = {}

    def register(self, name: str, service: T) -> None:
        self._services[name] = service

    def resolve(self, name: str) -> T:
        return self._services[name]
