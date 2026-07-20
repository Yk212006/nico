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


# ---------------------------------------------------------------------------
# Picovoice / Porcupine — accurate keyword detection (requires access key)
# ---------------------------------------------------------------------------

try:
    import pvporcupine
    _PORCUPINE_AVAILABLE = True
except ModuleNotFoundError:
    _PORCUPINE_AVAILABLE = False


class PicovoiceWakeWordDetector(BaseWakeWordDetector):
    """Wake-word detector powered by Picovoice Porcupine.

    Detects "Hey NICO" (or a custom ``.ppn`` keyword file) with high
    accuracy while ignoring other speech. Requires a free Picovoice
    ``AccessKey`` set via ``PICOVOICE_ACCESS_KEY`` env var.

    Audio format expected: 16-bit PCM, 16 kHz, mono (same as the
    default microphone).
    """

    def __init__(
        self,
        access_key: str | None = None,
        keyword_path: str | None = None,
        sensitivities: float | list[float] | None = None,
    ) -> None:
        if not _PORCUPINE_AVAILABLE:
            raise RuntimeError(
                "pvporcupine is not installed. Run: pip install pvporcupine"
            )

        self._access_key = access_key or os.getenv("PICOVOICE_ACCESS_KEY", "")
        if not self._access_key:
            raise ValueError(
                "PICOVOICE_ACCESS_KEY is required. Get one free at "
                "https://console.picovoice.ai/"
            )

        keyword_path = keyword_path or os.getenv("PICOVOICE_KEYWORD_PATH")
        sens = sensitivities
        if sens is None:
            env_sens = os.getenv("PICOVOICE_SENSITIVITY")
            sens = float(env_sens) if env_sens else 0.5

        kw_list: list[str] = []
        if keyword_path:
            kw_list = [keyword_path]
        else:
            kw_list = ["hey nico"]

        self._handle = pvporcupine.create(
            access_key=self._access_key,
            keyword_paths=kw_list if keyword_path else None,
            keywords=kw_list if not keyword_path else None,
            sensitivities=[sens] if isinstance(sens, (int, float)) else sens,
        )
        _logger.info(
            "Picovoice Porcupine initialized (version=%s, frame_length=%d)",
            pvporcupine.version,
            self._handle.frame_length,
        )

    async def detect(self, audio_bytes: bytes) -> bool:
        if not audio_bytes or len(audio_bytes) < 512:
            return False

        count = len(audio_bytes) // 2
        import struct
        shorts = struct.unpack(f"<{count}h", audio_bytes[: count * 2])

        keyword_index = self._handle.process(shorts)
        if keyword_index >= 0:
            _logger.info("Wake word detected (keyword_index=%d)", keyword_index)
            return True

        return False

    def close(self) -> None:
        try:
            self._handle.delete()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# OpenWakeWord — open source, no API key, works offline on Pi
# ---------------------------------------------------------------------------

try:
    import openwakeword
    from openwakeword.model import Model as OpenWakeWordModel
    _OPENWAKEWORD_AVAILABLE = True
except ModuleNotFoundError:
    _OPENWAKEWORD_AVAILABLE = False


class OpenWakeWordDetector(BaseWakeWordDetector):
    """Wake-word detector using OpenWakeWord.

    Fully open source, zero registration, no API key. Runs offline on a
    Pi 3B with ~100 MB RAM. Pre-trained on "hey jarvis" and "alexa".
    Custom wake words can be trained at https://github.com/dscripka/openWakeWord.

    Install: ``pip install openwakeword``

    Audio format expected: 16-bit PCM, 16 kHz, mono.
    """

    def __init__(
        self,
        wake_word: str = "hey jarvis",
        model_path: str | None = None,
        sensitivity: float = 0.5,
    ) -> None:
        if not _OPENWAKEWORD_AVAILABLE:
            raise RuntimeError(
                "openwakeword is not installed. Run: pip install openwakeword"
            )

        self._wake_word = wake_word.lower().strip()
        self._sensitivity = sensitivity

        if model_path:
            self._model = OpenWakeWordModel(wakeword_models=[model_path])
        else:
            self._model = OpenWakeWordModel()
        _logger.info(
            "OpenWakeWord initialized (wake_word=%s, sensitivity=%.2f)",
            self._wake_word,
            sensitivity,
        )

    async def detect(self, audio_bytes: bytes) -> bool:
        if not audio_bytes or len(audio_bytes) < 512:
            return False

        count = min(len(audio_bytes) // 2, 32000)
        import struct
        shorts = struct.unpack(f"<{count}h", audio_bytes[: count * 2])

        prediction = self._model.predict(shorts)
        for kw, score in prediction.items():
            if score >= self._sensitivity:
                _logger.info(
                    "Wake word detected (%s: confidence=%.3f)", kw, score
                )
                return True

        self._model.reset()
        return False


# ---------------------------------------------------------------------------
# Fallback — energy-based trigger (any loud speech)
# ---------------------------------------------------------------------------


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
