from nico.app import NicoApp
from nico.config.settings import Settings


def test_app_voice_initially_disabled() -> None:
    app = NicoApp(settings=Settings(default_provider="openai"))
    assert app.voice_pipeline is None


def test_app_voice_enabled_with_setting() -> None:
    app = NicoApp(
        settings=Settings(default_provider="openai", enable_voice=True)
    )
    assert app.voice_pipeline is not None


def test_app_audio_output_registered_with_voice_enabled() -> None:
    app = NicoApp(
        settings=Settings(default_provider="openai", enable_voice=True)
    )
    audio_output = app.registry.resolve("audio_output")
    assert audio_output is not None


def test_app_voice_pipeline_registered() -> None:
    app = NicoApp(
        settings=Settings(default_provider="openai", enable_voice=True)
    )
    pipeline = app.registry.resolve("voice_pipeline")
    assert pipeline is not None


def test_app_voice_chat_returns_none_when_disabled() -> None:
    import asyncio
    app = NicoApp(settings=Settings(default_provider="openai"))
    result = asyncio.run(app.voice_chat())
    assert result is None
