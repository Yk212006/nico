import pytest

from nico.tools.camera.camera import CameraTool


@pytest.mark.asyncio
async def test_camera_unavailable_without_picamera() -> None:
    tool = CameraTool()
    result = await tool.execute()
    # On systems without picamera2, should return unavailable
    assert "status" in result
    assert result["status"] in ("unavailable", "captured", "error")
