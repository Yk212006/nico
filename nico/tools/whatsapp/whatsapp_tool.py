from __future__ import annotations

import os
from typing import Any

_WHATSAPP_WEB_AVAILABLE = False
_ASYNC_PLAYWRIGHT_AVAILABLE = False

try:
    from playwright.async_api import async_playwright
    _ASYNC_PLAYWRIGHT_AVAILABLE = True
except ModuleNotFoundError:
    pass

WHATSAPP_DATA_DIR = os.path.expanduser("~/.nico/whatsapp_data")


class WhatsAppTool:
    """Send WhatsApp messages via WhatsApp Web automation."""

    name = "whatsapp"
    description = "Send a WhatsApp message to a phone number via WhatsApp Web"
    category = "messaging"
    timeout_seconds = 60.0
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "phone": {
                "type": "string",
                "description": "Recipient phone number with country code (e.g. +919876543210)",
            },
            "message": {
                "type": "string",
                "description": "Message text to send",
            },
            "confirmed": {
                "type": "boolean",
                "description": "Must be true to execute send",
            },
        },
        "required": ["phone", "message"],
    }

    @property
    def available(self) -> bool:
        return _ASYNC_PLAYWRIGHT_AVAILABLE

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        if not self.available:
            return {
                "status": "unavailable",
                "missing": "playwright",
                "message": (
                    "Playwright is required for WhatsApp Web. "
                    "Install with: pip install playwright && python -m playwright install chromium"
                ),
            }

        phone = str(kwargs.get("phone", ""))
        message = str(kwargs.get("message", ""))
        confirmed = bool(kwargs.get("confirmed", False))

        if not phone or not message:
            return {"status": "error", "message": "Both 'phone' and 'message' are required"}

        if not confirmed:
            return {
                "status": "requires_confirmation",
                "message": f"Sending a WhatsApp message to {phone} requires confirmation.",
            }

        return await self._send(phone, message)

    async def _send(self, phone: str, message: str) -> dict[str, Any]:
        os.makedirs(WHATSAPP_DATA_DIR, exist_ok=True)

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch_persistent_context(
                    WHATSAPP_DATA_DIR,
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                page = browser.pages[0] if browser.pages else await browser.new_page()
                await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
                await page.wait_for_timeout(5000)

                try:
                    await page.wait_for_selector('[data-testid="conversation-list"]', timeout=30000)
                except Exception:
                    return {
                        "status": "error",
                        "message": (
                            "WhatsApp Web QR scan timeout or login failed. "
                            "Please ensure WhatsApp Web is linked by scanning the QR code."
                        ),
                    }

                chat_url = f"https://web.whatsapp.com/send?phone={phone}"
                await page.goto(chat_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)

                try:
                    await page.wait_for_selector('[data-testid="conversation-compose-box-input"]', timeout=20000)
                except Exception:
                    await browser.close()
                    return {
                        "status": "error",
                        "message": f"Could not open chat for {phone}. Verify the number is valid and on WhatsApp.",
                    }

                input_box = page.locator('[data-testid="conversation-compose-box-input"]')
                await input_box.fill(message)
                await page.wait_for_timeout(500)

                send_button = page.locator('[data-testid="compose-btn-send"]')
                await send_button.click()
                await page.wait_for_timeout(2000)

                await browser.close()

                return {
                    "status": "sent",
                    "phone": phone,
                    "message": f"WhatsApp message sent to {phone}.",
                }
        except Exception as exc:
            return {
                "status": "error",
                "message": f"WhatsApp send failed: {exc}",
            }
