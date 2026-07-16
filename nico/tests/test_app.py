import asyncio

from nico.app import NicoApp
from nico.config.settings import Settings


def test_app_initializes_and_chat_returns_response() -> None:
    app = NicoApp(settings=Settings(default_provider="openai"))

    response = asyncio.run(app.chat("Hello NICO"))

    assert response.startswith("OpenAI response")
