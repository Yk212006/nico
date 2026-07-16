import asyncio

import pytest

from nico.app import NicoApp
from nico.brain.openai_provider import OpenAIProvider
from nico.brain.router import ProviderRouter
from nico.config.settings import Settings


@pytest.mark.asyncio
async def test_router_preserves_history_across_provider_switches() -> None:
    router = ProviderRouter({"openai": OpenAIProvider(), "claude": OpenAIProvider()}, default_provider="openai")

    first = await router.chat("Hello")
    assert "OpenAI response" in first

    router.handle_command("Use Claude")
    second = await router.chat("How are you?")

    assert router.state.active_provider == "claude"
    assert len(router.state.history) == 4


def test_nico_app_routes_commands() -> None:
    app = NicoApp(settings=Settings(default_provider="openai"))

    result = asyncio.run(app.chat("Use Gemini"))
    assert result == "Switched provider to gemini"
