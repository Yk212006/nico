from __future__ import annotations

import os
import pathlib
from typing import Any

try:
    from picamera2 import Picamera2
    _PICAMERA = True
except ImportError:
    _PICAMERA = False


class CameraTool:
    """Captures images from a Raspberry Pi camera module.

    On non-Pi systems or when the camera is unavailable, returns a
    clear message indicating the feature is not supported.
    """

    name = "camera"
    description = "Capture a photo using the Raspberry Pi camera module"
    category = "hardware"
    timeout_seconds = 15.0
    requires_confirmation = False
    parameters = {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "Optional path to save the captured image (default: /tmp/nico_capture.jpg)",
            },
        },
    }

    def __init__(self, files_root: str | None = None) -> None:
        root_env = os.getenv("NICO_FILES_ROOT", "~/nico_files")
        self._root = pathlib.Path(files_root or root_env).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, filepath: str) -> pathlib.Path:
        target = (self._root / filepath.lstrip("/\\")).resolve()
        if not str(target).startswith(str(self._root)):
            raise PermissionError(f"Path '{filepath}' escapes the sandbox at '{self._root}'")
        return target

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        if not _PICAMERA:
            return {
                "status": "unavailable",
                "message": "Camera is not available on this system. The picamera2 library is required.",
            }

        raw_path = str(kwargs.get("filepath", "capture.jpg"))
        try:
            filepath = str(self._safe_path(raw_path))
        except PermissionError as exc:
            return {"status": "error", "error": str(exc)}
        try:
            import asyncio
            camera = Picamera2()
            config = camera.create_still_configuration()
            camera.configure(config)
            camera.start()
            await asyncio.sleep(0.5)
            camera.capture_file(filepath)
            camera.stop()
            camera.close()
            return {
                "status": "captured",
                "filepath": filepath,
                "message": f"Photo captured and saved to {filepath}",
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
