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
async def test_lifecycle_tracks_running_state() -> None:
    service = DummyService()
    lifecycle = AppLifecycle([service])

    assert lifecycle.state() == "stopped"

    await lifecycle.start()
    assert lifecycle.state() == "running"

    await lifecycle.stop()
    assert lifecycle.state() == "stopped"
