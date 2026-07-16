from __future__ import annotations

import logging
from abc import ABC, abstractmethod

_logger = logging.getLogger("nico.audio.microphone")

try:
    import pyaudio
    _PYAUDIO = True
except ImportError:
    _PYAUDIO = False


class BaseMicrophone(ABC):
    """Abstraction for capturing raw audio."""

    @abstractmethod
    def capture(self) -> bytes:
        """Capture a chunk of raw audio from the input device.

        Returns:
            Raw audio bytes (typically 16-bit PCM, 16kHz, mono).
        """
        raise NotImplementedError


class DefaultMicrophone(BaseMicrophone):
    """Microphone driver using PyAudio.

    Falls back to silent dummy byte generation if pyaudio is not installed
    or no audio inputs are found.
    """

    def __init__(self, device_index: int = -1, rate: int = 16000, chunk_size: int = 1024) -> None:
        self.device_index = device_index
        self.rate = rate
        self.chunk_size = chunk_size
        self._p = None
        self._stream = None

        if _PYAUDIO:
            try:
                self._p = pyaudio.PyAudio()
                # Find default input if -1
                idx = device_index if device_index >= 0 else None
                self._stream = self._p.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.rate,
                    input=True,
                    input_device_index=idx,
                    frames_per_buffer=self.chunk_size,
                )
                _logger.info("PyAudio input stream initialized successfully.")
            except Exception as exc:
                _logger.warning("Failed to open PyAudio input stream: %s", exc)
                self._stream = None

    def capture(self) -> bytes:
        """Read audio frame bytes from the input device stream."""
        if self._stream is not None:
            try:
                # Read without blocking the whole thread if possible
                return self._stream.read(self.chunk_size, exception_on_overflow=False)
            except Exception as exc:
                _logger.debug("Microphone capture read error: %s", exc)
                return b""

        # Silent stub fallback
        # 16-bit PCM mono = 2 bytes per sample
        return b"\x00" * (self.chunk_size * 2)

    def close(self) -> None:
        """Release audio stream and clean up resources."""
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
        if self._p:
            try:
                self._p.terminate()
            except Exception:
                pass
        _logger.info("Microphone driver closed.")
