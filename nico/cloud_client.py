"""NICO Cloud Client — runs on the Raspberry Pi, relays to the cloud server.

This is the thin client that connects your Pi sensors, GPIO, and voice
to the NICO cloud server.

Usage:
    python -m nico.cloud_client --server https://your-cloud-server:8080
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("nico.cloud_client")


class CloudClient:
    """Connects to NICO Cloud Server, sends sensor data and receives commands."""

    def __init__(
        self,
        server_url: str | None = None,
        api_key: str | None = None,
        device_id: str | None = None,
        poll_interval: float = 30.0,
    ) -> None:
        self.server_url = (server_url or os.getenv("NICO_CLOUD_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("NICO_CLOUD_API_KEY", "")
        self.device_id = device_id or os.getenv("NICO_DEVICE_ID", "pi-3b")
        self.poll_interval = poll_interval

        if not self.server_url:
            raise ValueError(
                "Server URL required. Set NICO_CLOUD_URL or pass --server"
            )

        self._http = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        self._running = False
        self._sensor_data: dict[str, Any] = {}

    async def _health_check(self) -> bool:
        try:
            resp = await self._http.get(f"{self.server_url}/api/health")
            return resp.status_code == 200
        except Exception:
            return False

    async def _send_sensors(self) -> None:
        """Read local sensors and push to cloud."""
        data = await self._read_sensors()
        try:
            resp = await self._http.post(
                f"{self.server_url}/api/devices/{self.device_id}/sensors",
                json=data,
                headers=self._headers(),
            )
            if resp.status_code == 200:
                logger.debug("Sensor data sent: %s", data)
        except Exception as exc:
            logger.warning("Failed to send sensor data: %s", exc)

    async def _poll_commands(self) -> None:
        """Poll the cloud for pending GPIO / device commands."""
        try:
            resp = await self._http.get(
                f"{self.server_url}/api/devices/{self.device_id}/commands",
                headers=self._headers(),
            )
            if resp.status_code == 200:
                commands = resp.json().get("commands", [])
                for cmd in commands:
                    await self._execute_command(cmd)
        except Exception as exc:
            logger.debug("Command poll failed: %s", exc)

    async def _execute_command(self, cmd: dict[str, Any]) -> None:
        action = cmd.get("action", "")
        params = cmd.get("params", {})
        logger.info("Executing command: %s %s", action, params)
        result: dict[str, Any] = {"status": "unknown"}

        if action == "gpio_write":
            pin = params.get("pin")
            value = params.get("value")
            if pin is not None and value is not None:
                try:
                    import RPi.GPIO as GPIO

                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, value)
                    result = {"status": "ok", "pin": pin, "value": value}
                except Exception as exc:
                    result = {"status": "error", "error": str(exc)}
        elif action == "gpio_read":
            pin = params.get("pin")
            if pin is not None:
                try:
                    import RPi.GPIO as GPIO

                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(pin, GPIO.IN)
                    val = GPIO.input(pin)
                    result = {"status": "ok", "pin": pin, "value": val}
                except Exception as exc:
                    result = {"status": "error", "error": str(exc)}

        try:
            await self._http.post(
                f"{self.server_url}/api/devices/{self.device_id}/commands/{cmd.get('id', '')}/result",
                json=result,
                headers=self._headers(),
            )
        except Exception as exc:
            logger.warning("Failed to report command result: %s", exc)

    async def _read_sensors(self) -> dict[str, Any]:
        """Read DHT sensor and return values."""
        data: dict[str, Any] = {
            "timestamp": time.time(),
            "device_id": self.device_id,
        }
        # Try DHT sensor
        try:
            import board
            import adafruit_dht

            dht = adafruit_dht.DHT22(board.D4)
            data["temperature"] = dht.temperature
            data["humidity"] = dht.humidity
        except Exception:
            pass  # No DHT sensor connected
        # CPU temp
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                data["cpu_temp"] = round(int(f.read().strip()) / 1000, 1)
        except Exception:
            pass
        return data

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def chat(self, message: str) -> str:
        """Send a chat message to the cloud server (programmatic)."""
        resp = await self._http.post(
            f"{self.server_url}/api/chat",
            json={"message": message},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()["response"]

    async def run(self) -> None:
        """Main loop: health check, sensor push, command poll."""
        self._running = True
        logger.info(
            "Cloud Client starting — server=%s, device=%s",
            self.server_url,
            self.device_id,
        )

        if not await self._health_check():
            logger.warning("Cloud server unreachable at %s", self.server_url)

        while self._running:
            try:
                await self._send_sensors()
                await self._poll_commands()
            except Exception as exc:
                logger.error("Loop error: %s", exc)
            await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        self._running = False


async def _async_main(server: str, api_key: str, device_id: str) -> None:
    client = CloudClient(
        server_url=server,
        api_key=api_key,
        device_id=device_id,
    )

    def _signal_handler() -> None:
        logger.info("Shutting down...")
        client.stop()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows
            pass

    await client.run()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="NICO Cloud Client for Raspberry Pi")
    parser.add_argument("--server", help="Cloud server URL (e.g. https://nico.example.com:8080)")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--device-id", default="pi-3b", help="Unique device identifier")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    server = args.server or os.getenv("NICO_CLOUD_URL", "")
    api_key = args.api_key or os.getenv("NICO_CLOUD_API_KEY", "")

    if not server:
        parser.error("Server URL required. Use --server or set NICO_CLOUD_URL")

    print(f"  NICO Cloud Client")
    print(f"  Server:  {server}")
    print(f"  Device:  {args.device_id}")
    print(f"  Press Ctrl+C to stop")
    print()

    asyncio.run(_async_main(server, api_key, args.device_id))


if __name__ == "__main__":
    main()
