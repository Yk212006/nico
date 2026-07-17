from __future__ import annotations

import base64
import os
from email.mime.text import MIMEText
from typing import Any

from nico.integrations.google.credentials import api_get, api_post, get_credentials

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


class GmailIntegration:
    """Gmail Integration via REST API."""

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
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Gmail is not configured. Set GOOGLE_CREDENTIALS_FILE to enable.", "messages": []}

        try:
            params: dict[str, Any] = {"maxResults": max_results}
            if query:
                params["q"] = query

            data = await api_get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                creds,
                params=params,
            )

            messages_summary = []
            for msg in data.get("messages", []):
                detail = await api_get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
                    creds,
                    params={"format": "metadata", "metadataHeaders[]": ["Subject", "From", "Date"]},
                )
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

            return {"status": "ok", "messages": messages_summary, "source": "Google Gmail"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "messages": []}

    async def send_message(self, to: str, subject: str, body: str) -> dict[str, Any]:
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Gmail is not configured. Set GOOGLE_CREDENTIALS_FILE to enable."}

        try:
            message = MIMEText(body)
            message["to"] = to
            message["from"] = self.from_address or "me"
            message["subject"] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            result = await api_post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                creds,
                json_body={"raw": raw_message},
            )

            return {"status": "sent", "id": result.get("id"), "to": to, "source": "Google Gmail"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
