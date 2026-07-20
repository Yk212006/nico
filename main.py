from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from nico.app import NicoApp
from nico.pi_runtime import build_pi_settings, is_raspberry_pi

_logger = logging.getLogger("nico.main")


async def _voice_loop(app: NicoApp) -> None:
    """Continuous voice-activated smart speaker loop."""
    if app.voice_pipeline is None:
        _logger.error("Voice pipeline not available. Set NICO_ENABLE_VOICE=true.")
        return

    print(f"{app.settings.assistant_name} voice assistant is ready. Say the wake word to start.")
    print("Press Ctrl+C to exit.")

    while True:
        try:
            result = await app.voice_chat()
            if result is None:
                await asyncio.sleep(0.5)
                continue
            if not result.strip():
                continue
            _logger.info("Response: %s", result)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            _logger.error("Voice loop error: %s", exc)
            await asyncio.sleep(1)


async def _repl_loop(app: NicoApp) -> None:
    """Text-based REPL for keyboard interaction."""
    print(f"{app.settings.assistant_name} is ready.")
    print("Commands: 'exit' to quit, 'analyze <path> [prompt]' for vision")

    while True:
        try:
            message = input("You: ")
        except KeyboardInterrupt:
            break
        except EOFError:
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
            response = await app.analyze_image(image_bytes, prompt=prompt)
        else:
            response = await app.chat(raw)
        print(f"{app.settings.assistant_name}: {response}")


def main() -> None:
    settings = build_pi_settings() if is_raspberry_pi() else None
    app = NicoApp(settings=settings)

    asyncio.run(app.lifecycle.start())

    try:
        if app.settings.enable_voice and app.voice_pipeline is not None:
            asyncio.run(_voice_loop(app))
        else:
            asyncio.run(_repl_loop(app))
    except KeyboardInterrupt:
        pass
    finally:
        asyncio.run(app.lifecycle.stop())


if __name__ == "__main__":
    main()
