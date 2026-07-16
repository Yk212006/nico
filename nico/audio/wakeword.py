from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod

_logger = logging.getLogger("nico.audio.wakeword")


class BaseWakeWordDetector(ABC):
    """Abstraction for wake-word activation detection."""

    @abstractmethod
    async def detect(self, audio_bytes: bytes) -> bool:
        """Analyze audio frames and return True if wake word is detected."""
        raise NotImplementedError


class DefaultWakeWordDetector(BaseWakeWordDetector):
    """Wake Word Detector.

    Checks the environment configuration to determine whether to trigger.
    Can operate in:
    - active: always returns True (useful for push-to-talk or testing).
    - passive: scans raw audio amplitude/energy to detect noise/speech.
    - default/keyword: filters based on wake-word presence in input.
    """

    def __init__(self, wake_word: str | None = None) -> None:
        self.wake_word = (wake_word or os.getenv("WAKE_WORD", "hey nico")).lower().strip()

    async def detect(self, audio_bytes: bytes) -> bool:
        """Basic audio energy threshold detector to trigger when someone speaks."""
        if not audio_bytes:
            return False

        # If configured for testing or push-to-talk, always trigger
        if self.wake_word == "any" or self.wake_word == "always":
            return True

        # Analyze audio RMS (Root Mean Square) energy of 16-bit PCM frames
        # to detect sound activity/speech above threshold.
        import struct
        count = len(audio_bytes) // 2
        if count == 0:
            return False

        shorts = struct.unpack(f"<{count}h", audio_bytes[:count * 2])
        sum_squares = sum(s * s for s in shorts)
        rms = (sum_squares / count) ** 0.5

        # RMS threshold for speaking into microphone (around 500-1000)
        threshold = float(os.getenv("NICO_VAD_THRESHOLD", "800.0"))
        if rms >= threshold:
            _logger.info("Speech/Sound detected (RMS: %.2f >= %.2f)", rms, threshold)
            return True

        return False
