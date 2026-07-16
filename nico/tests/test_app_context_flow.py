import asyncio

from nico.app import NicoApp
from nico.config.settings import Settings


def test_app_chat_updates_context_and_memory() -> None:
    app = NicoApp(settings=Settings(default_provider="openai"))

    response = asyncio.run(app.chat("Tell me about the weather"))

    assert "Tool result" in response
    assert app.context.last_topic == "weather"
    assert app.context.followup_count == 1
    assert app.memory_manager.conversation.messages[-1]["content"].startswith("Tool result")
