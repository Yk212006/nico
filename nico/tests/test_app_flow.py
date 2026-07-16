import asyncio

from nico.app import NicoApp
from nico.config.settings import Settings
from nico.orchestrator import IntentOrchestrator


def test_app_uses_orchestrator_for_weather_requests() -> None:
    app = NicoApp(settings=Settings(default_provider="openai"))
    app.orchestrator = IntentOrchestrator(tool_manager=app.tool_manager)

    response = asyncio.run(app.chat("what is the weather in london"))

    assert "weather" in response.lower() or "london" in response.lower()
