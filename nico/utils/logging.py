from __future__ import annotations

import logging
import os
from typing import Any

# Secret-related key fragments to strip from log output.
_SECRET_FRAGMENTS = frozenset(
    {"key", "secret", "token", "password", "passwd", "credential", "auth"}
)


def get_logger(name: str, level: str | None = None) -> logging.Logger:
    """Return a configured logger for structured event logging.

    The log level defaults to the value of the ``NICO_LOG_LEVEL`` environment
    variable (falling back to ``INFO`` if unset) so every module shares a
    consistent level without importing :mod:`nico.config.settings` directly.

    Args:
        name:  Logger name, typically ``"nico.<module>"``.
        level: Optional override for this specific logger's level.
    """
    logger = logging.getLogger(name)

    effective_level = level or os.getenv("NICO_LOG_LEVEL", "INFO")
    logger.setLevel(getattr(logging, effective_level.upper(), logging.INFO))
    logger.propagate = True

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-8s %(name)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger.addHandler(handler)

    return logger


def _is_sensitive(key: str) -> bool:
    """Return ``True`` if a context key looks like it may contain a secret."""
    lowered = key.lower()
    return any(fragment in lowered for fragment in _SECRET_FRAGMENTS)


def log_event(logger: logging.Logger, event: str, **context: Any) -> None:
    """Log a structured event, automatically redacting any sensitive values.

    Values whose key contains a secret-related fragment (``key``, ``secret``,
    ``token``, ``password``, etc.) are replaced with ``"[REDACTED]"`` so they
    never appear in logs.

    Args:
        logger:  A :class:`logging.Logger` instance.
        event:   Short event name, e.g. ``"provider_selected"``.
        **context: Arbitrary key=value pairs to include in the log line.
    """
    safe_context = {
        k: "[REDACTED]" if _is_sensitive(k) else v
        for k, v in context.items()
    }
    payload = " ".join(f"{k}={v}" for k, v in safe_context.items())
    logger.info("event=%s%s", event, f" {payload}" if payload else "")


def log_error(logger: logging.Logger, event: str, exc: Exception, **context: Any) -> None:
    """Log a structured error event with exception information.

    Args:
        logger: A :class:`logging.Logger` instance.
        event:  Short error event name, e.g. ``"provider_failed"``.
        exc:    The exception that was raised.
        **context: Additional key=value context (secrets are redacted).
    """
    safe_context = {
        k: "[REDACTED]" if _is_sensitive(k) else v
        for k, v in context.items()
    }
    payload = " ".join(f"{k}={v}" for k, v in safe_context.items())
    logger.error(
        "event=%s exc_type=%s exc=%s%s",
        event,
        type(exc).__name__,
        exc,
        f" {payload}" if payload else "",
    )
