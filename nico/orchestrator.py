from __future__ import annotations

import re
from typing import Any

from nico.tools.manager import ToolManager


class IntentOrchestrator:
    """Routes natural-language requests to the appropriate subsystem.

    Extracts arguments from the query to avoid hardcoding parameters
    during tool execution.
    """

    def __init__(self, tool_manager: ToolManager) -> None:
        self.tool_manager = tool_manager

    async def handle(self, text: str) -> dict[str, Any]:
        lowered = text.lower().strip()
        kwargs: dict[str, Any] = {}

        # 1. Weather Intent
        if "weather" in lowered:
            # Try to extract city name: "weather in <city>" or "weather of <city>"
            match = re.search(r"weather (?:in|for|at|of)\s+([a-zA-Z\s]+)", lowered)
            city = match.group(1).strip() if match else "london"
            # Strip trailing question marks etc.
            city = re.sub(r"[^\w\s]", "", city).strip()
            return {
                "intent": "tool",
                "tool_name": "weather",
                "reason": "weather request",
                "tool_kwargs": {"city": city},
            }

        # 2. GPIO control
        if "gpio" in lowered or "pin" in lowered:
            # Try to extract pin number
            pin_match = re.search(r"(?:pin|gpio)\s*(\d+)", lowered)
            pin = int(pin_match.group(1)) if pin_match else 17
            action = "read"
            if "high" in lowered or "on" in lowered or "set" in lowered:
                action = "set_high"
            elif "low" in lowered or "off" in lowered:
                action = "set_low"
            elif "toggle" in lowered:
                action = "toggle"

            confirmed = "confirm" in lowered or "yes" in lowered
            return {
                "intent": "tool",
                "tool_name": "gpio",
                "reason": "gpio control",
                "tool_kwargs": {"pin": pin, "action": action, "confirmed": confirmed},
            }

        # 3. System Info / OS / Python
        if "system" in lowered or "python" in lowered or "os" in lowered:
            return {
                "intent": "tool",
                "tool_name": "system_info",
                "reason": "system information request",
                "tool_kwargs": {},
            }

        # 4. News Intent
        if "news" in lowered or "headlines" in lowered:
            return {
                "intent": "tool",
                "tool_name": "news",
                "reason": "news request",
                "tool_kwargs": {"count": 5},
            }

        # 5. Google Classroom (before generic file ops)
        if "classroom" in lowered or "course" in lowered or "assignment" in lowered or "coursework" in lowered or "submission" in lowered:
            cmd = "list_courses"
            course_id = ""
            coursework_id = ""
            if "coursework" in lowered or "assignment" in lowered:
                cmd = "list_coursework"
                id_match = re.search(r"course(?:\s+id)?\s*[:=]?\s*([a-zA-Z0-9_]+)", lowered)
                if id_match:
                    course_id = id_match.group(1)
            elif "submission" in lowered:
                cmd = "list_submissions"
                id_match = re.search(r"course(?:\s+id)?\s*[:=]?\s*([a-zA-Z0-9_]+)", lowered)
                if id_match:
                    course_id = id_match.group(1)
                cw_match = re.search(r"coursework(?:\s+id)?\s*[:=]?\s*([a-zA-Z0-9_]+)", lowered)
                if cw_match:
                    coursework_id = cw_match.group(1)
            return {
                "intent": "tool",
                "tool_name": "classroom",
                "reason": "classroom request",
                "tool_kwargs": {"command": cmd, "course_id": course_id, "coursework_id": coursework_id},
            }

        # 6. Google Drive (before generic file ops)
        if "drive" in lowered or "google drive" in lowered:
            cmd = "list"
            file_id = ""
            query = ""
            if "read" in lowered or "open" in lowered:
                cmd = "read"
                id_match = re.search(r"file(?:\s+id)?\s*[:=]?\s*([a-zA-Z0-9_\-]+)", lowered)
                if id_match:
                    file_id = id_match.group(1)
            elif "search" in lowered or "find" in lowered:
                cmd = "search"
                query_match = re.search(r"(?:search|find)\s+(.+?)(?:files|in\s+drive|$)", lowered)
                if query_match:
                    query = query_match.group(1).strip()
            elif "info" in lowered or "details" in lowered:
                cmd = "info"
                id_match = re.search(r"file(?:\s+id)?\s*[:=]?\s*([a-zA-Z0-9_\-]+)", lowered)
                if id_match:
                    file_id = id_match.group(1)
            return {
                "intent": "tool",
                "tool_name": "drive",
                "reason": "drive request",
                "tool_kwargs": {"command": cmd, "file_id": file_id, "query": query},
            }

        # 7. File Operations
        if "file" in lowered or "read" in lowered or "write" in lowered:
            action = "list"
            path = ""
            content = ""
            if "read" in lowered:
                action = "read"
            elif "write" in lowered or "save" in lowered:
                action = "write"
            elif "delete" in lowered or "remove" in lowered:
                action = "delete"

            # Try to extract file path and content
            # e.g., "write hello to note.txt"
            path_match = re.search(r"(?:file|path|to|from)\s+([a-zA-Z0-9_\-\./]+)", lowered)
            if path_match:
                candidate = path_match.group(1)
                if ".." in candidate:
                    path = ""
                    path_match = None
            if path_match:
                path = path_match.group(1).strip()
            
            # Simple content extraction
            if action == "write":
                content_match = re.search(r"write\s+(.+?)\s+(?:to|in|file)", lowered)
                if content_match:
                    content = content_match.group(1).strip()

            return {
                "intent": "tool",
                "tool_name": "files",
                "reason": "file management",
                "tool_kwargs": {"action": action, "path": path, "content": content},
            }

        # 6. Email Intent
        if "email" in lowered or "gmail" in lowered:
            action = "list"
            to = ""
            subject = ""
            body = ""
            if "send" in lowered or "compose" in lowered:
                action = "send"
                # try to extract recipient
                to_match = re.search(r"to\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", lowered)
                if to_match:
                    to = to_match.group(1).strip()

            return {
                "intent": "integration",
                "tool_name": "email",
                "reason": "email request",
                "tool_kwargs": {"action": action, "to": to, "subject": subject, "body": body},
            }

        # 7. Calendar Intent
        if "calendar" in lowered or "event" in lowered or "schedule" in lowered:
            return {
                "intent": "integration",
                "tool_name": "calendar",
                "reason": "calendar request",
                "tool_kwargs": {"max_results": 5},
            }

        # 8. Google Home control
        if "light" in lowered or "turn on" in lowered or "home" in lowered:
            device = "living_room"
            if "bedroom" in lowered:
                device = "bedroom"
            elif "kitchen" in lowered:
                device = "kitchen"
            return {
                "intent": "integration",
                "tool_name": "home",
                "reason": "home control request",
                "tool_kwargs": {"device": device},
            }

        # 9. Image / Vision analysis
        if ("image" in lowered or "picture" in lowered or "photo" in lowered
                or "describe" in lowered or "vision" in lowered):
            path = ""
            path_match = re.search(
                r"(?:image|picture|photo|file)\s+(?:at|in|from|of)?\s*"
                r"([a-zA-Z0-9_\-\.\/:\\\@]+(?:\.[a-zA-Z0-9]+))", lowered
            )
            if path_match:
                path = path_match.group(1).strip()
            return {
                "intent": "tool",
                "tool_name": "describe_image",
                "reason": "image analysis request",
                "tool_kwargs": {"image_path": path, "prompt": text},
            }

        # 10. Display / OLED
        if "display" in lowered or "oled" in lowered or "show on screen" in lowered:
            msg_match = re.search(r"(?:display|show|message)\s+(.+?)(?:$|on\s+display)", lowered)
            message = msg_match.group(1).strip() if msg_match else text
            return {
                "intent": "tool",
                "tool_name": "display",
                "reason": "display request",
                "tool_kwargs": {"message": message},
            }

        # 11. Sensors / Temperature
        if "sensor" in lowered or "temperature" in lowered or "cpu temp" in lowered:
            return {
                "intent": "tool",
                "tool_name": "sensors",
                "reason": "sensor reading request",
                "tool_kwargs": {"sensor_type": "temperature"},
            }

        # 12. Hardware Shutdown / Restart
        if "shutdown" in lowered or "restart" in lowered:
            tool_name = "shutdown" if "shutdown" in lowered else "restart"
            confirmed = "confirm" in lowered or "yes" in lowered
            return {
                "intent": "hardware",
                "tool_name": tool_name,
                "reason": "system control request",
                "tool_kwargs": {"confirm": confirmed},
            }

        return {
            "intent": "chat",
            "tool_name": None,
            "reason": "general conversation",
            "tool_kwargs": {},
        }
