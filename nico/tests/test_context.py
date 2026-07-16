import pytest

from nico.context import ConversationContext


@pytest.mark.asyncio
async def test_context_tracks_last_topic_and_followup() -> None:
    context = ConversationContext()
    await context.update("What is the weather in London?")
    await context.update("What about tomorrow?")

    assert context.last_topic == "weather"
    assert context.last_user_message == "What about tomorrow?"
    assert context.followup_count == 2
