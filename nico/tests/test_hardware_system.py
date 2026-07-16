import pytest
from unittest.mock import patch

from nico.hardware.system import SystemController


@pytest.mark.asyncio
async def test_system_controller_dispatches_shutdown_and_restart() -> None:
    with patch("nico.hardware.system.subprocess.Popen") as mock_popen:
        controller = SystemController(allow_system_control=True)

        shutdown_result = await controller.handle_action("shutdown", confirm=False)
        restart_result = await controller.handle_action("restart", confirm=True)

        assert shutdown_result["status"] == "requires_confirmation"
        assert restart_result["status"] == "executed"
        assert restart_result["action"] == "restart"
        mock_popen.assert_any_call(["shutdown", "/r", "/t", "0"])
