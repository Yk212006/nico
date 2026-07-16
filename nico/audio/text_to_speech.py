from __future__ import annotations

import logging
import os
import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator

_logger = logging.getLogger("nico.audio.tts")

try:
    import pyttsx3
    _PYTTSX3 = True
except ImportError:
    _PYTTSX3 = False

try:
    from gtts import gTTS
    _GTTS = True
except ImportError:
    _GTTS = False

try:
    import httpx
    _HTTPX = True
except ModuleNotFoundError:
    _HTTPX = False


class BaseTextToSpeech(ABC):
    """Abstraction for converting text to speech audio."""

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Synthesize text into audio file bytes (WAV or MP3 format)."""
        raise NotImplementedError

    async def stream_synthesize(self, text: str) -> AsyncIterator[bytes]:
        """Stream TTS audio chunks as they are produced.

        Default implementation yields the full result of :meth:`synthesize`
        as a single chunk.  Subclasses that support streaming (e.g. OpenAI)
        should override this for lower latency.
        """
        yield await self.synthesize(text)


class DefaultTextToSpeech(BaseTextToSpeech):
    """Text to Speech driver.

    Supports:
    - pyttsx3 (local, offline synthesis, ideal for Raspberry Pi)
    - gtts (Google Text-To-Speech online API)
    - openai (OpenAI TTS API with streaming support)
    - default (UTF-8 encoded bytes fallback)
    """

    _OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"
    _OPENAI_DEFAULT_VOICE = "nova"

    def __init__(self, provider: str | None = None, api_key: str | None = None) -> None:
        self.provider = provider or os.getenv("TTS_PROVIDER", "default")
        self.openai_key = api_key or os.getenv("OPENAI_API_KEY")
        self.openai_voice = os.getenv("OPENAI_TTS_VOICE", self._OPENAI_DEFAULT_VOICE)
        self._engine = None

        if self.provider == "pyttsx3" and _PYTTSX3:
            try:
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", 150)
                _logger.info("pyttsx3 offline TTS initialized.")
            except Exception as exc:
                _logger.warning("Failed to initialize pyttsx3: %s", exc)
                self._engine = None

    async def synthesize(self, text: str) -> bytes:
        clean_text = text.strip()
        if not clean_text:
            return b""

        # 1. pyttsx3 offline TTS
        if self.provider == "pyttsx3" and self._engine is not None:
            return await self._synthesize_pyttsx3(clean_text)

        # 2. gTTS online API
        if self.provider == "gtts" and _GTTS:
            return await self._synthesize_gtts(clean_text)

        # 3. OpenAI TTS API (non-streaming fallback)
        if self.provider == "openai" and self.openai_key and _HTTPX:
            chunks = [c async for c in self._synthesize_openai(clean_text)]
            if chunks:
                return b"".join(chunks)

        # 4. Default fallback (UTF-8 encoded string bytes)
        return clean_text.encode("utf-8")

    async def stream_synthesize(self, text: str) -> AsyncIterator[bytes]:
        clean_text = text.strip()
        if not clean_text:
            return

        if self.provider == "openai" and self.openai_key and _HTTPX:
            async for chunk in self._synthesize_openai(clean_text):
                yield chunk
            return

        # Non-streaming providers yield the full result in one chunk
        yield await self.synthesize(clean_text)

    async def _synthesize_pyttsx3(self, text: str) -> bytes:
        try:
            loop = asyncio.get_running_loop()
            temp_file = "temp_speech.wav"

            def _render():
                engine = pyttsx3.init()
                engine.setProperty("rate", 150)
                engine.save_to_file(text, temp_file)
                engine.runAndWait()

            await loop.run_in_executor(None, _render)
            if os.path.exists(temp_file):
                with open(temp_file, "rb") as f:
                    data = f.read()
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
                return data
        except Exception as exc:
            _logger.warning("pyttsx3 synthesis failed: %s", exc)
        return text.encode("utf-8")

    async def _synthesize_gtts(self, text: str) -> bytes:
        try:
            loop = asyncio.get_running_loop()
            temp_file = "temp_gtts.mp3"

            def _gtts_render():
                tts = gTTS(text=text, lang="en")
                tts.save(temp_file)

            await loop.run_in_executor(None, _gtts_render)
            if os.path.exists(temp_file):
                with open(temp_file, "rb") as f:
                    data = f.read()
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
                return data
        except Exception as exc:
            _logger.warning("gTTS synthesis failed: %s", exc)
        return text.encode("utf-8")

    async def _synthesize_openai(self, text: str) -> AsyncIterator[bytes]:
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    self._OPENAI_TTS_URL,
                    headers={"Authorization": f"Bearer {self.openai_key}"},
                    json={
                        "model": "tts-1",
                        "voice": self.openai_voice,
                        "input": text,
                        "response_format": "wav",
                    },
                    timeout=30.0,
                ) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            yield chunk
        except Exception as exc:
            _logger.warning("OpenAI TTS synthesis failed: %s", exc)
