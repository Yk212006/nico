import pytest

from nico.lifecycle import AppLifecycle


class DummyService:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


@pytest.mark.asyncio
async def test_lifecycle_starts_and_stops_services() -> None:
    service = DummyService()
    lifecycle = AppLifecycle([service])

    await lifecycle.start()
    await lifecycle.stop()

    assert service.started is True
    assert service.stopped is True
