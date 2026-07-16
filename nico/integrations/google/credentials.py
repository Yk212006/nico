"""Shared OAuth2 credential management for Google integrations."""

from __future__ import annotations

import logging
import os
from typing import Any

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    _GOOGLE_API = True
except ModuleNotFoundError:
    _GOOGLE_API = False

_logger = logging.getLogger("nico.integrations.google.credentials")


def get_credentials(
    scopes: list[str],
    credentials_file: str | None = None,
    token_file: str | None = None,
) -> Any | None:
    """Obtain OAuth2 credentials for Google APIs.

    Args:
        scopes: OAuth2 scope list for the desired API.
        credentials_file: Path to the client secrets JSON file.
        token_file: Path where the token will be cached.

    Returns:
        Credentials object if successful, ``None`` if unavailable.
    """
    if not _GOOGLE_API:
        _logger.debug("Google API libraries not installed")
        return None

    cred_file = credentials_file or os.getenv("GOOGLE_CREDENTIALS_FILE")
    tok_file = token_file or os.getenv("GOOGLE_TOKEN_FILE", "~/.nico/google_token.json")

    if not cred_file:
        _logger.debug("No Google credentials file configured")
        return None

    creds: Any = None
    token_path = os.path.expanduser(tok_file)
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, scopes)
        except Exception as exc:
            _logger.warning("Failed to load cached token: %s", exc)
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _logger.info("Refreshed expired credentials")
        except Exception as exc:
            _logger.warning("Failed to refresh credentials: %s", exc)
            creds = None
        else:
            _save_token(creds, token_path)
            return creds

    if not os.path.exists(cred_file):
        _logger.debug("Credentials file not found: %s", cred_file)
        return None

    try:
        flow = InstalledAppFlow.from_client_secrets_file(cred_file, scopes)
        creds = flow.run_local_server(port=0, open_browser=False)
        _save_token(creds, token_path)
        return creds
    except Exception as exc:
        _logger.warning("Failed to authenticate: %s", exc)
        return None


def _save_token(creds: Any, token_path: str) -> None:
    """Persist credentials to the token file."""
    try:
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    except Exception as exc:
        _logger.warning("Failed to save token: %s", exc)
