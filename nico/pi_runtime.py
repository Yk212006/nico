from __future__ import annotations

import os
import platform

from nico.config.settings import Settings


def _read_device_tree_model() -> str:
    try:
        with open("/proc/device-tree/model") as f:
            return f.read().strip().lower()
    except (OSError, FileNotFoundError):
        return ""


def is_raspberry_pi() -> bool:
    machine = platform.machine().lower()
    if "arm" not in machine and "aarch64" not in machine:
        return False
    model = _read_device_tree_model()
    if model and "raspberry pi" in model:
        return True
    return os.path.exists("/dev/gpiomem")


def build_pi_settings() -> Settings:
    return Settings(
        assistant_name=os.getenv("NICO_ASSISTANT_NAME", "NICO Pi"),
        default_provider=os.getenv("NICO_DEFAULT_PROVIDER", "openai"),
        log_level=os.getenv("NICO_LOG_LEVEL", "INFO"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        enable_tools=os.getenv("NICO_ENABLE_TOOLS", "true").lower() == "true",
        enable_memory=os.getenv("NICO_ENABLE_MEMORY", "false").lower() == "true",
    )
