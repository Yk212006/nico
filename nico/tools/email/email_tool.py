from __future__ import annotations

from typing import Any

from nico.integrations.google.gmail import GmailIntegration


class EmailTool:
    """NICO tool for reading and sending Gmail via GmailIntegration."""

    name = "email"
    description = "Read recent emails or send an email via Gmail"
    category = "google"
    timeout_seconds = 15.0
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "send"],
                "description": "Operation: 'list' to read messages, 'send' to compose",
            },
            "query": {
                "type": "string",
                "description": "Gmail search query for 'list' (e.g. 'is:unread')",
            },
            "to": {
                "type": "string",
                "description": "Recipient address for 'send'",
            },
            "subject": {
                "type": "string",
                "description": "Email subject for 'send'",
            },
            "body": {
                "type": "string",
                "description": "Email body for 'send'",
            },
            "max_results": {
                "type": "integer",
                "description": "Number of messages to list (default 5)",
            },
            "confirmed": {
                "type": "boolean",
                "description": "Must be true to execute send operations",
            },
        },
        "required": ["action"],
    }

    def __init__(self, integration: GmailIntegration | None = None) -> None:
        self._integration = integration or GmailIntegration()

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        action = str(kwargs.get("action", "list"))
        if action == "list":
            query = kwargs.get("query")
            max_results = int(kwargs.get("max_results", 5))
            return await self._integration.list_messages(
                query=query, max_results=max_results
            )
        if action == "send":
            confirmed = bool(kwargs.get("confirmed", False))
            if not confirmed:
                return {
                    "status": "requires_confirmation",
                    "message": "Sending an email requires confirmation.",
                }
            to = str(kwargs.get("to", ""))
            subject = str(kwargs.get("subject", ""))
            body = str(kwargs.get("body", ""))
            if not to:
                return {"error": "Recipient address ('to') is required"}
            return await self._integration.send_message(
                to=to, subject=subject, body=body
            )
        return {"error": f"Unknown email action: {action}"}
