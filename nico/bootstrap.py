from __future__ import annotations

from typing import Any

from nico.config.settings import Settings
from nico.registry import ServiceRegistry


class AppBootstrap:
    """Bootstraps the application container.

    Initializes the service registry and configures key dependency providers.
    """

    def __init__(self, services: dict[str, Any] | None = None) -> None:
        self.registry = ServiceRegistry()
        for name, service in (services or {}).items():
            self.registry.register(name, service)

    def create_app(self, settings: Settings | None = None) -> Any:
        """Initialize and return a configured NicoApp instance."""
        from nico.app import NicoApp  # noqa: PLC0415

        # Initialize settings first
        app_settings = settings or Settings.from_env()
        self.registry.register("settings", app_settings)

        app = NicoApp(settings=app_settings)
        return app
