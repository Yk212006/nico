from __future__ import annotations

import asyncio
from pathlib import Path

from nico.app import NicoApp
from nico.pi_runtime import build_pi_settings, is_raspberry_pi


def main() -> None:
    settings = build_pi_settings() if is_raspberry_pi() else None
    app = NicoApp(settings=settings)
    print(f"{app.settings.assistant_name} is ready.")
    print("Commands: 'exit' to quit, 'analyze <path> [prompt]' for vision")

    while True:
        try:
            message = input("You: ")
        except KeyboardInterrupt:
            break
        raw = message.strip()
        if raw.lower() in {"exit", "quit"}:
            break

        if raw.lower().startswith("analyze "):
            parts = raw.split(None, 2)
            image_path = Path(parts[1])
            if not image_path.exists():
                print(f"Error: image not found at '{image_path}'")
                continue
            prompt = parts[2] if len(parts) > 2 else "Describe this image in detail"
            image_bytes = image_path.read_bytes()
            response = asyncio.run(app.analyze_image(image_bytes, prompt=prompt))
        else:
            response = asyncio.run(app.chat(raw))
        print(f"{app.settings.assistant_name}: {response}")


if __name__ == "__main__":
    main()
