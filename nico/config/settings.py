from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Application configuration loaded from environment variables.

    All settings have safe defaults so the assistant runs without any
    external services configured.  Set the corresponding env var to
    enable each optional feature.
    """

    # Core identity
    assistant_name: str = os.getenv("NICO_ASSISTANT_NAME", "NICO")
    default_provider: str = os.getenv("NICO_DEFAULT_PROVIDER", "openai")
    log_level: str = os.getenv("NICO_LOG_LEVEL", "INFO")

    # Feature flags
    enable_tools: bool = os.getenv("NICO_ENABLE_TOOLS", "true").lower() == "true"
    enable_memory: bool = os.getenv("NICO_ENABLE_MEMORY", "true").lower() == "true"
    allow_system_control: bool = (
        os.getenv("NICO_ALLOW_SYSTEM_CONTROL", "false").lower() == "true"
    )

    # Memory tuning
    max_memory_chars: int = int(os.getenv("NICO_MAX_MEMORY_CHARS", "8000"))

    # AI provider keys / models
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # Tool API keys
    openweathermap_api_key: Optional[str] = os.getenv("OPENWEATHERMAP_API_KEY")
    news_rss_url: str = os.getenv(
        "NEWS_RSS_URL", "https://feeds.bbci.co.uk/news/rss.xml"
    )
    files_root: str = os.path.expanduser(
        os.getenv("NICO_FILES_ROOT", "~/nico_files")
    )

    # Google workspace
    google_credentials_file: Optional[str] = os.getenv("GOOGLE_CREDENTIALS_FILE")
    google_token_file: str = os.path.expanduser(
        os.getenv("GOOGLE_TOKEN_FILE", "~/.nico/google_token.json")
    )
    google_calendar_id: str = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    gmail_from_address: Optional[str] = os.getenv("GMAIL_FROM_ADDRESS")
    google_tasks_list_id: str = os.getenv("GOOGLE_TASKS_LIST_ID", "@default")

    # Home Assistant
    home_assistant_url: str = os.getenv(
        "HOME_ASSISTANT_URL", "http://homeassistant.local:8123"
    )
    home_assistant_token: Optional[str] = os.getenv("HOME_ASSISTANT_TOKEN")

    # Google Assistant (for home device control)
    google_assistant_token_file: str = os.getenv(
        "GOOGLE_ASSISTANT_TOKEN_FILE", "~/.nico/assistant_token.json"
    )
    google_assistant_device_model_id: Optional[str] = os.getenv(
        "GOOGLE_ASSISTANT_DEVICE_MODEL_ID"
    )
    google_assistant_device_id: Optional[str] = os.getenv(
        "GOOGLE_ASSISTANT_DEVICE_ID"
    )

    # Voice / audio
    stt_provider: str = os.getenv("STT_PROVIDER", "default")
    tts_provider: str = os.getenv("TTS_PROVIDER", "default")
    openai_tts_voice: str = os.getenv("OPENAI_TTS_VOICE", "nova")
    wake_word: str = os.getenv("WAKE_WORD", "hey nico")
    audio_input_device: int = int(os.getenv("AUDIO_INPUT_DEVICE", "-1"))
    audio_output_device: int = int(os.getenv("AUDIO_OUTPUT_DEVICE", "-1"))
    vad_threshold: float = float(os.getenv("NICO_VAD_THRESHOLD", "800.0"))
    vad_silence_timeout: float = float(os.getenv("NICO_VAD_SILENCE_TIMEOUT", "1.5"))
    vad_max_record_seconds: float = float(os.getenv("NICO_VAD_MAX_RECORD_SECONDS", "10.0"))
    enable_voice: bool = os.getenv("NICO_ENABLE_VOICE", "false").lower() == "true"
    enable_interruption: bool = os.getenv("NICO_ENABLE_INTERRUPTION", "true").lower() == "true"

    @classmethod
    def from_env(cls) -> "Settings":
        """Create a Settings instance by reading from environment variables."""
        return cls()
