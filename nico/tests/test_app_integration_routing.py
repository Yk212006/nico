import asyncio

from nico.app import NicoApp
from nico.config.settings import Settings


def test_app_routes_calendar_request_to_dispatcher() -> None:
    app = NicoApp(settings=Settings(default_provider="openai"))

    response = asyncio.run(app.chat("show me my calendar events"))

    assert "Integration result" in response
    assert "events" in response


def test_app_routes_home_request_to_dispatcher() -> None:
    app = NicoApp(settings=Settings(default_provider="openai"))

    response = asyncio.run(app.chat("turn on the lights in the kitchen"))

    assert "Integration result" in response
    assert "device" in response
    assert "kitchen" in response


def test_app_routes_email_request_to_dispatcher() -> None:
    app = NicoApp(settings=Settings(default_provider="openai"))

    response = asyncio.run(app.chat("check my email"))

    assert "Integration result" in response
    assert "messages" in response
