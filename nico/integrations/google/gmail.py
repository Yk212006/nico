from __future__ import annotations

import base64
import os
from email.mime.text import MIMEText
from typing import Any

from nico.integrations.google.credentials import get_credentials

# Scopes required for Gmail operations
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


try:
    from googleapiclient.discovery import build as _build
    _GOOGLE_API = True
except ModuleNotFoundError:
    _GOOGLE_API = False


class GmailIntegration:
    """Gmail Integration service.

    Supports reading messages and sending messages. Uses official Google API
    libraries if configured, otherwise indicates the service is unavailable.
    """

    def __init__(
        self,
        credentials_file: str | None = None,
        token_file: str | None = None,
        from_address: str | None = None,
    ) -> None:
        self._credentials_file = credentials_file
        self._token_file = token_file
        self.from_address = from_address or os.getenv("GMAIL_FROM_ADDRESS")

    async def list_messages(self, query: str | None = None, max_results: int = 5) -> dict[str, Any]:
        """List recent email threads/messages."""
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Gmail is not configured. Set GOOGLE_CREDENTIALS_FILE to enable.", "messages": []}

        if not _GOOGLE_API:
            return {"status": "unavailable", "message": "Google API client libraries not installed.", "messages": []}

        try:
            import asyncio
            service = _build("gmail", "v1", credentials=creds)
            loop = asyncio.get_running_loop()

            def _fetch():
                results = service.users().messages().list(
                    userId="me", maxResults=max_results, q=query
                ).execute()
                messages_summary = []
                for msg in results.get("messages", []):
                    detail = service.users().messages().get(
                        userId="me", id=msg["id"], format="metadata",
                        metadataHeaders=["Subject", "From", "Date"]
                    ).execute()
                    headers = detail.get("payload", {}).get("headers", [])
                    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
                    sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
                    date = next((h["value"] for h in headers if h["name"] == "Date"), "")
                    messages_summary.append({
                        "id": msg["id"],
                        "subject": subject,
                        "from": sender,
                        "date": date,
                        "snippet": detail.get("snippet", ""),
                    })
                return messages_summary

            items = await loop.run_in_executor(None, _fetch)
            return {"status": "ok", "messages": items, "source": "Google Gmail"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "messages": []}

    async def send_message(self, to: str, subject: str, body: str) -> dict[str, Any]:
        """Send a new email message."""
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Gmail is not configured. Set GOOGLE_CREDENTIALS_FILE to enable."}

        if not _GOOGLE_API:
            return {"status": "unavailable", "message": "Google API client libraries not installed."}

        try:
            service = _build("gmail", "v1", credentials=creds)
            import asyncio
            loop = asyncio.get_running_loop()

            def _send():
                message = MIMEText(body)
                message["to"] = to
                message["from"] = self.from_address or "me"
                message["subject"] = subject
                raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
                
                send_result = service.users().messages().send(
                    userId="me", body={"raw": raw_message}
                ).execute()
                return send_result

            result = await loop.run_in_executor(None, _send)
            return {"status": "sent", "id": result.get("id"), "to": to, "source": "Google Gmail"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
