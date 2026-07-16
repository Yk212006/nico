import pytest

from nico.context import ConversationContext


@pytest.mark.asyncio
async def test_context_exposes_summary_and_snapshot() -> None:
    context = ConversationContext()
    await context.update("Tell me about the weather")

    summary = context.summary()
    snapshot = context.snapshot()

    assert "weather" in summary
    assert snapshot["last_topic"] == "weather"
    assert snapshot["followup_count"] == 1
