from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PROFILES: dict[str, dict[str, Any]] = {
    "default": {
        "provider": "openai",
        "enable_tools": True,
        "enable_memory": True,
    },
    "voice": {
        "provider": "claude",
        "enable_tools": True,
        "enable_memory": True,
    },
    "minimal": {
        "provider": "gemini",
        "enable_tools": False,
        "enable_memory": False,
    },
}


def load_profile(name: str) -> dict[str, Any]:
    """Load a named preset profile for the assistant runtime."""

    if name not in _PROFILES:
        raise KeyError(f"Unknown profile: {name}")
    return dict(_PROFILES[name])


def load_profile_from_file(path: str | Path) -> dict[str, Any]:
    """Load a profile from a JSON file on disk."""

    profile_path = Path(path)
    with profile_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Validate a profile dictionary and raise ValueError on invalid settings."""

    provider = profile.get("provider")
    if provider not in {"openai", "claude", "gemini"}:
        raise ValueError(f"Unsupported provider: {provider}")

    if not isinstance(profile.get("enable_tools", True), bool):
        raise ValueError("enable_tools must be a boolean")

    if not isinstance(profile.get("enable_memory", True), bool):
        raise ValueError("enable_memory must be a boolean")

    return profile
