import pytest

from nico.notifications import NotificationService


@pytest.mark.asyncio
async def test_notification_desktop_simulated() -> None:
    service = NotificationService()
    result = await service.send("Test Title", "Test Message")
    assert result["title"] == "Test Title"
    assert result["message"] == "Test Message"
    assert result["desktop_sent"] in (True, "simulated")


@pytest.mark.asyncio
async def test_notification_voice_disabled_by_default() -> None:
    service = NotificationService()
    result = await service.send("Test", "Hello", desktop=False)
    assert result["desktop_sent"] is False
    assert result["voice_sent"] is False


@pytest.mark.asyncio
async def test_notification_with_tts() -> None:
    class FakeTTS:
        async def synthesize(self, text: str) -> bytes:
            return b"audio"

    service = NotificationService(tts_service=FakeTTS())
    result = await service.send("Test", "Hello", desktop=False, voice=True)
    assert result["voice_sent"] is True
