from __future__ import annotations

import os
from typing import Any

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]


class WeatherTool:
    """Returns real weather data from OpenWeatherMap (free tier).

    Falls back gracefully to a labelled placeholder when no API key is
    configured so the application remains fully functional offline and
    during unit tests.
    """

    name = "weather"
    description = "Get current weather conditions and forecast for a city"
    category = "web"
    timeout_seconds = 10.0
    max_retries = 1
    parameters = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "City name, e.g. 'London' or 'New York'",
            },
            "units": {
                "type": "string",
                "enum": ["metric", "imperial", "standard"],
                "description": "Temperature units (default: metric)",
            },
        },
        "required": ["city"],
    }

    _BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENWEATHERMAP_API_KEY")

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        city: str = str(kwargs.get("city", "unknown"))
        units: str = str(kwargs.get("units", "metric"))
        unit_label = {"metric": "°C", "imperial": "°F", "standard": "K"}.get(
            units, "°C"
        )

        if not self.api_key or httpx is None:
            return self._stub(city, unit_label)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self._BASE_URL,
                    params={
                        "q": city,
                        "appid": self.api_key,
                        "units": units,
                    },
                    timeout=8.0,
                )
                if response.status_code == 404:
                    return {"error": f"City not found: {city}", "city": city}
                response.raise_for_status()
                data = response.json()

                weather_desc = (
                    data.get("weather", [{}])[0].get("description", "unknown")
                    if data.get("weather")
                    else "unknown"
                )
                main = data.get("main", {})
                wind = data.get("wind", {})
                clouds = data.get("clouds", {})

                return {
                    "city": data.get("name", city),
                    "country": data.get("sys", {}).get("country", ""),
                    "description": weather_desc.capitalize(),
                    "temperature": f"{main.get('temp', '?')}{unit_label}",
                    "feels_like": f"{main.get('feels_like', '?')}{unit_label}",
                    "humidity": f"{main.get('humidity', '?')}%",
                    "wind_speed": f"{wind.get('speed', '?')} m/s",
                    "cloudiness": f"{clouds.get('all', '?')}%",
                    "source": "OpenWeatherMap",
                }
        except Exception as exc:
            return {
                "error": f"Weather lookup failed: {exc}",
                "city": city,
                **self._stub(city, unit_label),
            }

    @staticmethod
    def _stub(city: str, unit_label: str) -> dict[str, str]:
        return {
            "city": city,
            "description": "Sunny with light breeze (offline demo data)",
            "temperature": f"22{unit_label}",
            "humidity": "55%",
            "source": "offline",
        }
