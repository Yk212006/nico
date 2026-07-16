from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nico.brain.router import ProviderRouter


class DescribeImageTool:
    """Analyzes an image using AI vision capabilities.

    Reads an image file from disk and sends it to the active AI provider
    for analysis. Falls back gracefully when offline.
    """

    name = "describe_image"
    description = "Analyze an image using AI vision. Provide the image file path."
    category = "vision"
    timeout_seconds = 30.0
    max_retries = 1
    parameters = {
        "type": "object",
        "properties": {
            "image_path": {
                "type": "string",
                "description": "Path to the image file (e.g. /tmp/photo.jpg)",
            },
            "prompt": {
                "type": "string",
                "description": "Question or instruction about the image",
                "default": "Describe this image in detail",
            },
        },
        "required": ["image_path"],
    }

    def __init__(self, router: ProviderRouter | None = None) -> None:
        self.router = router

    async def execute(self, image_path: str, prompt: str = "Describe this image in detail", **kwargs: Any) -> str:
        path = Path(image_path)
        if not path.exists():
            return f"Error: File not found at '{image_path}'"
        if not path.is_file():
            return f"Error: '{image_path}' is not a file"

        try:
            image_bytes = path.read_bytes()
        except Exception as exc:
            return f"Error reading image: {exc}"

        if self.router is None:
            return "Vision analysis unavailable: no AI provider configured"

        try:
            result = await self.router.vision(prompt, image_bytes)
            return result
        except Exception as exc:
            return f"Vision analysis failed: {exc}"
