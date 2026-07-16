import pytest

from nico.audio.microphone import BaseMicrophone
from nico.audio.speech_to_text import BaseSpeechToText
from nico.audio.text_to_speech import BaseTextToSpeech
from nico.audio.wakeword import BaseWakeWordDetector
from nico.audio.voice_pipeline import VoicePipeline


class FakeMicrophone(BaseMicrophone):
    def __init__(self, payload: bytes = b"audio") -> None:
        self.payload = payload

    def capture(self) -> bytes:
        return self.payload


class FakeSTT(BaseSpeechToText):
    async def transcribe(self, audio_bytes: bytes) -> str:
        return "hello nico"


class FakeTTS(BaseTextToSpeech):
    async def synthesize(self, text: str) -> bytes:
        return text.encode("utf-8")


class FakeWakeWord(BaseWakeWordDetector):
    async def detect(self, audio_bytes: bytes) -> bool:
        return True


@pytest.mark.asyncio
async def test_voice_pipeline_transcribes_and_speaks() -> None:
    async def handler(text: str) -> str:
        return f"reply:{text}"

    pipeline = VoicePipeline(
        microphone=FakeMicrophone(),
        speech_to_text=FakeSTT(),
        text_to_speech=FakeTTS(),
        wake_word_detector=FakeWakeWord(),
        conversation_handler=handler,
    )

    result = await pipeline.process_audio()

    assert result.transcript == "hello nico"
    assert result.response == "reply:hello nico"
    assert result.audio == b"reply:hello nico"
