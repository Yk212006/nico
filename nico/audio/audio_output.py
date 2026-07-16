from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator

_logger = logging.getLogger("nico.audio.output")

try:
    import pyaudio
    _PYAUDIO = True
except ImportError:
    _PYAUDIO = False


class BaseAudioOutput(ABC):
    """Abstraction for playing audio to the speaker."""

    @abstractmethod
    async def play(self, audio_bytes: bytes) -> None:
        """Play audio bytes to the speaker (blocking until done)."""
        raise NotImplementedError

    @abstractmethod
    async def play_stream(self, chunks: AsyncIterator[bytes]) -> None:
        """Play a stream of audio chunks in real-time."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Immediately stop playback."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Release audio resources."""
        raise NotImplementedError


class DefaultAudioOutput(BaseAudioOutput):
    """Speaker driver using PyAudio.

    Falls back to no-op (silent) if PyAudio is not installed.
    """

    def __init__(self, device_index: int | None = None, rate: int = 24000) -> None:
        self._device_index = device_index
        self._rate = rate
        self._p: pyaudio.PyAudio | None = None
        self._stream: pyaudio.Stream | None = None
        self._playing = False

        if _PYAUDIO:
            try:
                self._p = pyaudio.PyAudio()
            except Exception as exc:
                _logger.warning("Failed to initialize PyAudio output: %s", exc)
                self._p = None

    def _open_stream(self) -> pyaudio.Stream | None:
        if self._p is None:
            return None
        try:
            stream = self._p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self._rate,
                output=True,
                output_device_index=self._device_index,
                frames_per_buffer=1024,
            )
            return stream
        except Exception as exc:
            _logger.warning("Failed to open audio output stream: %s", exc)
            return None

    async def play(self, audio_bytes: bytes) -> None:
        if not audio_bytes:
            return
        stream = self._open_stream()
        if stream is None:
            _logger.info("[SILENT PLAYBACK] %d bytes", len(audio_bytes))
            return
        self._playing = True
        try:
            import asyncio
            loop = asyncio.get_running_loop()

            def _write():
                stream.write(audio_bytes)

            await loop.run_in_executor(None, _write)
        except Exception as exc:
            _logger.warning("Audio playback failed: %s", exc)
        finally:
            self._playing = False
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass

    async def play_stream(self, chunks: AsyncIterator[bytes]) -> None:
        stream = self._open_stream()
        if stream is None:
            async for chunk in chunks:
                _logger.debug("[SILENT STREAM] %d bytes", len(chunk))
            return
        self._playing = True
        try:
            import asyncio
            loop = asyncio.get_running_loop()

            def _write(chunk: bytes) -> None:
                stream.write(chunk)

            async for chunk in chunks:
                if not self._playing:
                    break
                if chunk:
                    await loop.run_in_executor(None, _write, chunk)
        except Exception as exc:
            _logger.warning("Streaming playback failed: %s", exc)
        finally:
            self._playing = False
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass

    def stop(self) -> None:
        self._playing = False

    def close(self) -> None:
        self.stop()
        if self._stream:
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._p:
            try:
                self._p.terminate()
            except Exception:
                pass
            self._p = None
