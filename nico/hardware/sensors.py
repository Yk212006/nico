from __future__ import annotations

import os
import random
import time
from typing import Any

try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    _GPIO_AVAILABLE = False


class SensorMonitor:
    """Monitors system temperature, environmental sensors, and hardware sensors.

    Supports reading Raspberry Pi CPU temperature, DHT11/22 temperature/humidity,
    and ultrasonic distance sensors.
    """

    def __init__(self) -> None:
        pass

    async def read_temperature(self) -> dict[str, Any]:
        """Read system/CPU temperature. Falls back to a mock reading on desktop."""
        # 1. Try Linux thermal zone (Raspberry Pi CPU)
        temp_path = "/sys/class/thermal/thermal_zone0/temp"
        if os.path.exists(temp_path):
            try:
                with open(temp_path, "r") as f:
                    temp_raw = int(f.read().strip())
                return {
                    "temperature_c": round(temp_raw / 1000.0, 1),
                    "unit": "C",
                    "device": "cpu_thermal_zone0",
                }
            except Exception:
                pass

        # 2. Try macOS/Windows simulator mock
        return {
            "temperature_c": round(random.uniform(38.0, 48.0), 1),
            "unit": "C",
            "device": "cpu_simulated",
        }

    async def read_dht(self, pin: int = 4, sensor_type: str = "DHT22") -> dict[str, Any]:
        """Read temperature/humidity from DHT sensor."""
        result = self._try_adafruit_dht(pin, sensor_type)
        if result:
            return result

        # Simulated fallback
        return {
            "status": "simulated",
            "temperature_c": 22.5,
            "humidity": 45.0,
            "device": f"{sensor_type}_simulated",
        }

    @staticmethod
    def _try_adafruit_dht(pin: int, sensor_type: str) -> dict[str, Any] | None:
        try:
            import Adafruit_DHT  # noqa: PLC0415
            sensor = Adafruit_DHT.DHT22 if sensor_type == "DHT22" else Adafruit_DHT.DHT11
            humidity, temp = Adafruit_DHT.read_retry(sensor, pin)
            if humidity is not None and temp is not None:
                return {
                    "status": "ok",
                    "temperature_c": round(temp, 1),
                    "humidity": round(humidity, 1),
                    "device": sensor_type,
                }
        except Exception:
            pass

        try:
            import board  # noqa: PLC0415
            import adafruit_dht  # noqa: PLC0415
            sensor_cls = adafruit_dht.DHT22 if sensor_type == "DHT22" else adafruit_dht.DHT11
            pin_attr = getattr(board, f"D{pin}", None)
            if pin_attr is None:
                return None
            dht = sensor_cls(pin_attr)
            try:
                temp = dht.temperature
                humidity = dht.humidity
                if humidity is not None and temp is not None:
                    return {
                        "status": "ok",
                        "temperature_c": round(temp, 1),
                        "humidity": round(humidity, 1),
                        "device": sensor_type,
                    }
            finally:
                try:
                    dht.exit()
                except Exception:
                    pass
        except Exception:
            pass

        return None

    async def read_distance(self, trigger_pin: int = 18, echo_pin: int = 24) -> dict[str, Any]:
        """Read ultrasonic sensor distance in cm."""
        if not _GPIO_AVAILABLE:
            return {
                "status": "simulated",
                "distance_cm": round(random.uniform(10.0, 150.0), 1),
                "device": "HC-SR04_simulated",
            }

        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(trigger_pin, GPIO.OUT)
            GPIO.setup(echo_pin, GPIO.IN)

            # Triggerpulse
            GPIO.output(trigger_pin, GPIO.LOW)
            time.sleep(0.000002)
            GPIO.output(trigger_pin, GPIO.HIGH)
            time.sleep(0.00001)
            GPIO.output(trigger_pin, GPIO.LOW)

            # Measure echo duration
            start_time = time.time()
            stop_time = time.time()

            # Wait for echo to start
            timeout_start = time.time()
            while GPIO.input(echo_pin) == 0:
                start_time = time.time()
                if start_time - timeout_start > 0.05:  # 50ms timeout
                    return {"status": "error", "message": "Echo timeout (0)"}

            # Wait for echo to end
            timeout_start = time.time()
            while GPIO.input(echo_pin) == 1:
                stop_time = time.time()
                if stop_time - timeout_start > 0.05:  # 50ms timeout
                    return {"status": "error", "message": "Echo timeout (1)"}

            elapsed = stop_time - start_time
            # Speed of sound: 34300 cm/s (roundtrip / 2)
            distance = (elapsed * 34300) / 2

            return {
                "status": "ok",
                "distance_cm": round(distance, 1),
                "device": "HC-SR04",
            }
        except Exception as exc:
            return {"status": "error", "message": str(exc)}
