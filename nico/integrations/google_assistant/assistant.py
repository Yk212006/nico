from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

SCOPES = ["https://www.googleapis.com/auth/assistant-sdk-prototype"]

try:
    from google.auth.transport.grpc import secure_authorized_channel
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    _AUTH_AVAILABLE = True
except ModuleNotFoundError:
    _AUTH_AVAILABLE = False

try:
    from google.assistant.embedded.v1alpha2 import embedded_assistant_pb2
    from google.assistant.embedded.v1alpha2 import embedded_assistant_pb2_grpc
    _ASSISTANT_AVAILABLE = True
except ModuleNotFoundError:
    _ASSISTANT_AVAILABLE = False

_logger = logging.getLogger("nico.integrations.google_assistant")

_ASSISTANT_ENDPOINT = "embeddedassistant.googleapis.com"


class GoogleAssistantIntegration:
    """Controls Google Home devices via the Google Assistant SDK.

    Sends natural-language text commands (e.g. "turn on the living room
    light") to the Google Assistant gRPC API, which executes them on
    devices linked to the user's Google account.
    """

    def __init__(
        self,
        credentials_file: str | None = None,
        token_file: str | None = None,
        device_model_id: str | None = None,
        device_id: str | None = None,
        language_code: str | None = None,
    ) -> None:
        self._credentials_file = credentials_file or os.getenv("GOOGLE_CREDENTIALS_FILE")
        self._token_file = token_file or os.getenv("GOOGLE_ASSISTANT_TOKEN_FILE", "~/.nico/assistant_token.json")
        self._device_model_id = device_model_id or os.getenv("GOOGLE_ASSISTANT_DEVICE_MODEL_ID")
        self._device_id = device_id or os.getenv("GOOGLE_ASSISTANT_DEVICE_ID")
        self._language_code = language_code or os.getenv("GOOGLE_ASSISTANT_LANGUAGE_CODE", "en-IN")

    @property
    def available(self) -> bool:
        if not _AUTH_AVAILABLE:
            return False
        if not _ASSISTANT_AVAILABLE:
            return False
        if not self._credentials_file:
            return False
        if not os.path.exists(self._credentials_file):
            return False
        if not self._device_model_id:
            return False
        if not self._device_id:
            return False
        return True

    def _get_credentials(self) -> Credentials | None:
        if not _AUTH_AVAILABLE:
            _logger.debug("google-auth-oauthlib not installed")
            return None

        creds: Credentials | None = None
        token_path = os.path.expanduser(self._token_file)
        if os.path.exists(token_path):
            try:
                with open(token_path) as f:
                    creds = Credentials.from_authorized_user_info(json.load(f), SCOPES)
            except Exception as exc:
                _logger.warning("Failed to load cached token: %s", exc)

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                _save_token(creds, token_path)
            except Exception as exc:
                _logger.warning("Failed to refresh token: %s", exc)
                creds = None

        if creds and creds.valid:
            return creds

        if not os.path.exists(self._credentials_file):
            _logger.debug("Credentials file not found: %s", self._credentials_file)
            return None

        try:
            flow = InstalledAppFlow.from_client_secrets_file(self._credentials_file, SCOPES)
            creds = flow.run_local_server(port=0, open_browser=False)
            _save_token(creds, token_path)
            return creds
        except Exception as exc:
            _logger.warning("OAuth flow failed: %s", exc)
            return None

    async def send_command(self, text: str) -> dict[str, Any]:
        if not self.available:
            missing = self._missing()
            return {
                "status": "unavailable",
                "missing": missing,
                "message": f"Google Assistant not available. Missing: {', '.join(missing)}",
            }

        creds = self._get_credentials()
        if not creds:
            return {
                "status": "unconfigured",
                "message": "Could not obtain Google OAuth credentials. Set GOOGLE_CREDENTIALS_FILE.",
            }

        try:
            return await self._assist(creds, text)
        except Exception as exc:
            _logger.exception("Google Assistant command failed")
            return {"status": "error", "error": str(exc)}

    def _missing(self) -> list[str]:
        missing = []
        if not _AUTH_AVAILABLE:
            missing.append("google-auth-oauthlib")
        if not _ASSISTANT_AVAILABLE:
            missing.append("google-assistant-grpc")
        if not self._credentials_file:
            missing.append("GOOGLE_CREDENTIALS_FILE")
        if not self._device_model_id:
            missing.append("GOOGLE_ASSISTANT_DEVICE_MODEL_ID")
        if not self._device_id:
            missing.append("GOOGLE_ASSISTANT_DEVICE_ID")
        return missing

    async def _assist(self, creds: Credentials, text: str) -> dict[str, Any]:
        loop = asyncio.get_running_loop()

        def _run() -> dict[str, Any]:
            channel = secure_authorized_channel(creds, Request(), _ASSISTANT_ENDPOINT)
            stub = embedded_assistant_pb2_grpc.EmbeddedAssistantStub(channel)

            def gen():
                yield embedded_assistant_pb2.AssistRequest(
                    config=embedded_assistant_pb2.AssistConfig(
                        text_query=text,
                        audio_out_config=embedded_assistant_pb2.AudioOutConfig(
                            encoding="LINEAR16",
                            sample_rate_hertz=16000,
                        ),
                        dialog_state_in=embedded_assistant_pb2.DialogStateIn(
                            language_code=self._language_code,
                        ),
                        device_config=embedded_assistant_pb2.DeviceConfig(
                            device_id=str(self._device_id),
                            device_model_id=str(self._device_model_id),
                        ),
                    )
                )

            result: dict[str, Any] = {
                "status": "ok",
                "query": text,
                "display_text": "",
                "transcript": "",
                "audio_out": b"",
            }

            audio_chunks: list[bytes] = []

            for resp in stub.Assist(gen()):
                if resp.dialog_state_out.supplemental_display_text:
                    result["display_text"] = resp.dialog_state_out.supplemental_display_text
                if resp.speech_results:
                    parts = [sr.transcript for sr in resp.speech_results]
                    result["transcript"] += " ".join(parts)
                if resp.audio_out.audio_data:
                    audio_chunks.append(resp.audio_out.audio_data)

            if audio_chunks:
                result["audio_out"] = b"".join(audio_chunks)

            return result

        return await loop.run_in_executor(None, _run)


def _save_token(creds: Credentials, token_path: str) -> None:
    try:
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    except Exception as exc:
        _logger.warning("Failed to save token: %s", exc)
