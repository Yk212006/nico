from __future__ import annotations

import re

_PROMPT_INJECTION_PATTERNS = re.compile(
    r"(?i)(?:ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions"
    r"|forget\s+(?:all\s+)?(?:previous|prior)\s+instructions"
    r"|you\s+are\s+(?:now\s+)?(?:an?\s+)?(?:AI\s+)?(?:assistant|model)\s+named?\s+"
    r"|override\s+(?:mode|system|instructions)"
    r"|new\s+instructions?:\s*)",
)

_MAX_INPUT_LENGTH = 32_000


def sanitize_input(text: str) -> str:
    """Sanitize user input before sending to the LLM.

    * Strips null bytes and control characters (except tab/newline).
    * Truncates to ``_MAX_INPUT_LENGTH`` characters.
    """
    cleaned = text.replace("\x00", "")
    cleaned = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
    return cleaned[:_MAX_INPUT_LENGTH]


def detect_injection_attempt(text: str) -> bool:
    """Return ``True`` if the text looks like a prompt injection attempt."""
    return bool(_PROMPT_INJECTION_PATTERNS.search(text))
