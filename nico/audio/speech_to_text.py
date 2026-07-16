from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod

try:
    import httpx
    _HTTPX = True
except ModuleNotFoundError:
    _HTTPX = False

_logger = logging.getLogger("nico.audio.stt")


class BaseSpeechToText(ABC):
    """Abstraction for converting audio to text."""

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe raw audio bytes to a text string.

        Args:
            audio_bytes: Raw 16-bit PCM mono 16kHz audio bytes.
        """
        raise NotImplementedError


class DefaultSpeechToText(BaseSpeechToText):
    """Speech to Text driver.

    Supports Groq Whisper API (very fast) and OpenAI Whisper API, with
    graceful offline mock transcript fallback.
    """

    def __init__(self, provider: str | None = None, api_key: str | None = None) -> None:
        self.provider = provider or os.getenv("STT_PROVIDER", "default")
        self.openai_key = api_key or os.getenv("OPENAI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")

    async def transcribe(self, audio_bytes: bytes) -> str:
        if not audio_bytes or len(audio_bytes) < 100:
            return ""

        # 1. Groq Whisper transcription (low latency)
        if self.provider == "groq" and self.groq_key and _HTTPX:
            try:
                # Wrap raw PCM to an in-memory WAV container
                wav_data = self._pcm_to_wav(audio_bytes)
                async with httpx.AsyncClient() as client:
                    files = {"file": ("audio.wav", wav_data, "audio/wav")}
                    data = {"model": "whisper-large-v3"}
                    headers = {"Authorization": f"Bearer {self.groq_key}"}
                    response = await client.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        files=files,
                        data=data,
                        headers=headers,
                        timeout=15.0,
                    )
                    response.raise_for_status()
                    return response.json().get("text", "").strip()
            except Exception as exc:
                _logger.warning("Groq STT transcription failed: %s", exc)

        # 2. OpenAI Whisper transcription
        if self.provider == "whisper_openai" and self.openai_key and _HTTPX:
            try:
                wav_data = self._pcm_to_wav(audio_bytes)
                async with httpx.AsyncClient() as client:
                    files = {"file": ("audio.wav", wav_data, "audio/wav")}
                    data = {"model": "whisper-1"}
                    headers = {"Authorization": f"Bearer {self.openai_key}"}
                    response = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        files=files,
                        data=data,
                        headers=headers,
                        timeout=15.0,
                    )
                    response.raise_for_status()
                    return response.json().get("text", "").strip()
            except Exception as exc:
                _logger.warning("OpenAI Whisper STT failed: %s", exc)

        # 3. Default Simulated / Offline fallback
        return ""

    @staticmethod
    def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000) -> bytes:
        """Wrap raw PCM bytes with a standard WAV header."""
        import struct
        num_samples = len(pcm_data) // 2
        block_align = 2
        byte_rate = sample_rate * block_align
        
        # WAV Header fields
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + len(pcm_data),
            b"WAVE",
            b"fmt ",
            16,
            1,  # PCM
            1,  # Mono
            sample_rate,
            byte_rate,
            block_align,
            16,  # 16-bit
            b"data",
            len(pcm_data)
        )
        return header + pcm_data
