import os
import pytest

from nico.audio.text_to_speech import DefaultTextToSpeech, BaseTextToSpeech
from nico.audio.audio_output import BaseAudioOutput, DefaultAudioOutput
from nico.audio.voice_pipeline import VoicePipeline


class FakeTTS(BaseTextToSpeech):
    async def synthesize(self, text: str) -> bytes:
        return text.encode("utf-8")


class FakeAudioOutput(BaseAudioOutput):
    def __init__(self) -> None:
        self.last_audio: bytes | None = None
        self.last_chunks: list[bytes] = []
        self.stopped = False

    async def play(self, audio_bytes: bytes) -> None:
        self.last_audio = audio_bytes

    async def play_stream(self, chunks):
        async for chunk in chunks:
            self.last_chunks.append(chunk)

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_default_tts_fallback_returns_utf8() -> None:
    tts = DefaultTextToSpeech(provider="default")
    result = await tts.synthesize("hello")
    assert result == b"hello"


@pytest.mark.asyncio
async def test_default_tts_empty_text() -> None:
    tts = DefaultTextToSpeech(provider="default")
    result = await tts.synthesize("")
    assert result == b""


@pytest.mark.asyncio
async def test_default_tts_stream_fallback_yields_full_result() -> None:
    tts = DefaultTextToSpeech(provider="default")
    chunks = [c async for c in tts.stream_synthesize("hello")]
    assert chunks == [b"hello"]


@pytest.mark.asyncio
async def test_tts_stream_empty_text_yields_nothing() -> None:
    tts = DefaultTextToSpeech(provider="default")
    chunks = [c async for c in tts.stream_synthesize("")]
    assert chunks == []


@pytest.mark.asyncio
async def test_base_tts_stream_default_yields_synthesize_result() -> None:
    class MinimalTTS(BaseTextToSpeech):
        async def synthesize(self, text: str) -> bytes:
            return text.encode("utf-8")

    tts = MinimalTTS()
    chunks = [c async for c in tts.stream_synthesize("hi")]
    assert chunks == [b"hi"]


@pytest.mark.asyncio
async def test_audio_output_silent_playback() -> None:
    output = DefaultAudioOutput()
    # Should not raise even without PyAudio
    await output.play(b"")
    await output.play(b"audio data")
    output.close()


@pytest.mark.asyncio
async def test_audio_output_stop() -> None:
    output = DefaultAudioOutput()
    output.stop()
    assert output._playing is False
    output.close()


def test_fake_audio_output() -> None:
    output = FakeAudioOutput()
    assert output.last_audio is None
    assert output.stopped is False


@pytest.mark.asyncio
async def test_voice_pipeline_with_event_publishing() -> None:
    from nico.audio.microphone import BaseMicrophone
    from nico.audio.speech_to_text import BaseSpeechToText
    from nico.audio.wakeword import BaseWakeWordDetector

    class FakeMic(BaseMicrophone):
        def __init__(self):
            self.call_count = 0

        def capture(self) -> bytes:
            self.call_count += 1
            # Return silence bytes (well below threshold) for fast VAD completion
            return b"\x00\x00" * 512

    class FakeSTT(BaseSpeechToText):
        async def transcribe(self, audio_bytes: bytes) -> str:
            return "hello"

    class FakeWW(BaseWakeWordDetector):
        async def detect(self, audio_bytes: bytes) -> bool:
            return True

    async def handler(text: str) -> str:
        return f"reply:{text}"

    pipeline = VoicePipeline(
        microphone=FakeMic(),
        speech_to_text=FakeSTT(),
        text_to_speech=FakeTTS(),
        wake_word_detector=FakeWW(),
        conversation_handler=handler,
    )

    os.environ["NICO_VAD_THRESHOLD"] = "999999"
    try:
        result = await pipeline.process_audio(silence_timeout=0.1, max_record_seconds=0.5)
    finally:
        del os.environ["NICO_VAD_THRESHOLD"]

    assert result.transcript == "hello"
    assert result.response == "reply:hello"
    assert result.audio == b"reply:hello"


@pytest.mark.asyncio
async def test_voice_pipeline_empty_transcript_returns_empty_result() -> None:
    from nico.audio.microphone import BaseMicrophone
    from nico.audio.speech_to_text import BaseSpeechToText
    from nico.audio.wakeword import BaseWakeWordDetector

    class EmptyMic(BaseMicrophone):
        def capture(self) -> bytes:
            return b"\x00\x00" * 512

    class EmptySTT(BaseSpeechToText):
        async def transcribe(self, audio_bytes: bytes) -> str:
            return ""

    class AlwaysWW(BaseWakeWordDetector):
        async def detect(self, audio_bytes: bytes) -> bool:
            return True

    async def handler(text: str) -> str:
        return f"reply:{text}"

    pipeline = VoicePipeline(
        microphone=EmptyMic(),
        speech_to_text=EmptySTT(),
        text_to_speech=FakeTTS(),
        wake_word_detector=AlwaysWW(),
        conversation_handler=handler,
    )

    os.environ["NICO_VAD_THRESHOLD"] = "999999"
    try:
        result = await pipeline.process_audio(silence_timeout=0.1, max_record_seconds=0.5)
    finally:
        del os.environ["NICO_VAD_THRESHOLD"]

    assert result.transcript == ""
    assert result.response == ""
    assert result.audio == b""


def test_stop_playback_sets_flag() -> None:
    from nico.audio.microphone import BaseMicrophone
    from nico.audio.speech_to_text import BaseSpeechToText
    from nico.audio.wakeword import BaseWakeWordDetector

    class FakeMic(BaseMicrophone):
        def capture(self) -> bytes:
            return b"\x00\x00" * 512

    class FakeSTT(BaseSpeechToText):
        async def transcribe(self, audio_bytes: bytes) -> str:
            return "test"

    class FakeWW(BaseWakeWordDetector):
        async def detect(self, audio_bytes: bytes) -> bool:
            return True

    async def handler(text: str) -> str:
        return "ok"

    pipeline = VoicePipeline(
        microphone=FakeMic(),
        speech_to_text=FakeSTT(),
        text_to_speech=FakeTTS(),
        wake_word_detector=FakeWW(),
        conversation_handler=handler,
    )

    assert pipeline._is_speaking is False
    pipeline.stop_playback()
    assert pipeline._is_speaking is False
