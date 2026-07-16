from __future__ import annotations

import asyncio
import logging
import os
import struct
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from nico.audio.microphone import BaseMicrophone
from nico.audio.speech_to_text import BaseSpeechToText
from nico.audio.text_to_speech import BaseTextToSpeech
from nico.audio.wakeword import BaseWakeWordDetector

_logger = logging.getLogger("nico.audio.pipeline")


@dataclass
class VoicePipelineResult:
    """Container for the processed audio turn."""

    transcript: str
    response: str
    audio: bytes


class VoicePipeline:
    """Coordinates microphone capture, transcription, response generation, and speech synthesis.

    Implements a Voice Activity Detection (VAD) buffer to record until the
    user finishes speaking, and supports interruption via :meth:`stop_playback`.
    """

    def __init__(
        self,
        *,
        microphone: BaseMicrophone,
        speech_to_text: BaseSpeechToText,
        text_to_speech: BaseTextToSpeech,
        wake_word_detector: BaseWakeWordDetector,
        conversation_handler: Callable[[str], Awaitable[str]],
    ) -> None:
        self.microphone = microphone
        self.speech_to_text = speech_to_text
        self.text_to_speech = text_to_speech
        self.wake_word_detector = wake_word_detector
        self.conversation_handler = conversation_handler
        self._is_speaking = False

    async def process_audio(
        self,
        *,
        silence_timeout: float | None = None,
        max_record_seconds: float | None = None,
    ) -> VoicePipelineResult:
        """Run a single conversational audio turn.

        Listens for wake word, then records user speech (VAD), transcribes
        it, gets the text response, and synthesizes speech.

        Args:
            silence_timeout: Seconds of silence before recording stops
                             (default 1.5 or ``NICO_VAD_SILENCE_TIMEOUT`` env).
            max_record_seconds: Max recording duration
                                (default 10.0 or ``NICO_VAD_MAX_RECORD_SECONDS`` env).

        Returns:
            A :class:`VoicePipelineResult` with transcript, response, and audio.
        """
        silence_threshold = float(os.getenv("NICO_VAD_THRESHOLD", "800.0"))
        silence_limit = silence_timeout or float(os.getenv("NICO_VAD_SILENCE_TIMEOUT", "1.5"))
        max_record = max_record_seconds or float(os.getenv("NICO_VAD_MAX_RECORD_SECONDS", "10.0"))

        # 1. Listen for wake word/sound activation
        audio_buffer: list[bytes] = []
        _logger.debug("Listening for wake activation...")

        while True:
            chunk = self.microphone.capture()
            if not chunk:
                await asyncio.sleep(0.05)
                continue

            if await self.wake_word_detector.detect(chunk):
                audio_buffer.append(chunk)
                try:
                    from nico.events import WakeWordDetected, publish
                    await publish(WakeWordDetected(phrase="activation", confidence=1.0))
                except Exception:
                    pass
                break

            await asyncio.sleep(0.02)

        _logger.info("Wake word/activation detected! Starting recording...")

        # 2. Record until silence is detected (VAD Loop)
        try:
            from nico.events import ListeningStarted, publish
            await publish(ListeningStarted())
        except Exception:
            pass

        chunk_duration = 1024 / 16000  # seconds per chunk (~64ms)
        silence_chunks_limit = int(silence_limit / chunk_duration)
        max_chunks = int(max_record / chunk_duration)

        silence_counter = 0
        total_chunks = 0

        while total_chunks < max_chunks:
            chunk = self.microphone.capture()
            if not chunk:
                await asyncio.sleep(0.02)
                continue

            audio_buffer.append(chunk)
            total_chunks += 1

            # Energy check for VAD
            count = len(chunk) // 2
            if count > 0:
                shorts = struct.unpack(f"<{count}h", chunk[:count * 2])
                rms = (sum(s * s for s in shorts) / count) ** 0.5
                if rms < silence_threshold:
                    silence_counter += 1
                else:
                    if silence_counter > 0:
                        try:
                            from nico.events import VadSpeechDetected, publish
                            await publish(VadSpeechDetected(energy=rms))
                        except Exception:
                            pass
                    silence_counter = 0
            else:
                silence_counter += 1

            if silence_counter >= silence_chunks_limit:
                _logger.info("Silence detected. Stopping recording.")
                break

            await asyncio.sleep(0.01)

        try:
            from nico.events import ListeningEnded, publish
            await publish(ListeningEnded())
        except Exception:
            pass

        # Combine all recorded PCM bytes
        recorded_audio = b"".join(audio_buffer)

        # 3. Transcribe speech to text
        _logger.info("Transcribing...")
        transcript = await self.speech_to_text.transcribe(recorded_audio)
        _logger.info("User said: '%s'", transcript)

        if not transcript:
            return VoicePipelineResult(transcript="", response="", audio=b"")

        # 4. Generate conversation text response
        _logger.info("Generating response...")
        response_text = await self.conversation_handler(transcript)
        _logger.info("NICO: '%s'", response_text)

        # 5. Synthesize response to speech audio
        _logger.info("Synthesizing speech...")
        self._is_speaking = True
        try:
            from nico.events import SpeechStarted, publish
            await publish(SpeechStarted(text=response_text))
        except Exception:
            pass

        audio_bytes_out = await self.text_to_speech.synthesize(response_text)

        self._is_speaking = False
        try:
            from nico.events import SpeechEnded, publish
            await publish(SpeechEnded(text=response_text))
        except Exception:
            pass

        return VoicePipelineResult(
            transcript=transcript,
            response=response_text,
            audio=audio_bytes_out,
        )

    def stop_playback(self) -> None:
        """Interrupt current audio playback (e.g. if user starts speaking)."""
        self._is_speaking = False
        _logger.info("Speech playback interrupted.")
