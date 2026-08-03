from __future__ import annotations

from datetime import date, datetime, timezone

import httpx

from .config import OPENWEATHER_API_KEY, OPENWEATHER_BASE_URL
from .cities_data import CITIES, COUNTRY_NAMES
from .schemas import CitySuggestion, WeatherInfo


class WeatherError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class OpenWeatherClient:
    """Thin client around the OpenWeatherMap API (free tier)."""

    def __init__(self, api_key: str = OPENWEATHER_API_KEY, timeout: float = 15.0):
        self.api_key = api_key
        self.timeout = timeout

    def _get(self, path: str, params: dict) -> dict:
        if not self.api_key:
            raise WeatherError("OPENWEATHERMAP_API_KEY is not configured.", 500)
        url = f"{OPENWEATHER_BASE_URL}/{path}"
        params = {**params, "appid": self.api_key, "units": "metric"}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params)
        if response.status_code != 200:
            code = response.status_code
            if code == 401:
                raise WeatherError("Invalid OpenWeatherMap API key.", 500)
            if code == 404:
                raise WeatherError(f"City not found.", 404)
            raise WeatherError(
                f"OpenWeatherMap error: {response.text[:200]}", 502
            )
        return response.json()

    def fetch_weather_for_date(self, city: str, target: date) -> WeatherInfo:
        """Fetch weather for a city on a given date (today or within 5-day forecast)."""
        today = datetime.now(timezone.utc).date()
        if target < today:
            raise WeatherError(
                "The free OpenWeatherMap tier does not provide historical "
                "weather. Please pick today or a date within the next 5 days.",
                400,
            )

        if target == today:
            current = self._get("weather", {"q": city})
            return self._from_current(current, city)

        forecast = self._get("forecast", {"q": city})
        return self._from_forecast_day(forecast, city, target)

    def _from_current(self, data: dict, city: str) -> WeatherInfo:
        main = data["main"]
        weather = data["weather"][0]
        wind = data.get("wind", {})
        return WeatherInfo(
            city=data.get("name") or city,
            country=(data.get("sys", {}) or {}).get("country", ""),
            date=datetime.now(timezone.utc).date().isoformat(),
            temperature_c=main["temp"],
            feels_like_c=main.get("feels_like", main["temp"]),
            humidity_pct=main.get("humidity", 0),
            wind_speed_mps=wind.get("speed", 0.0),
            pressure_hpa=main.get("pressure", 0),
            condition=weather.get("main", ""),
            description=weather.get("description", ""),
            rain_pct=None,
            uv_index=None,
        )

    def _from_forecast_day(self, forecast: dict, city: str, target: date) -> WeatherInfo:
        city_name = (forecast.get("city", {}) or {}).get("name", city)
        country = (forecast.get("city", {}) or {}).get("country", "")

        entries = [
            e for e in forecast.get("list", [])
            if datetime.fromtimestamp(e["dt"], tz=timezone.utc).date() == target
        ]
        if not entries:
            raise WeatherError(
                f"No forecast data available for {target.isoformat()}.",
                404,
            )

        temp = [e["main"]["temp"] for e in entries]
        rain_pct = max(
            (e.get("pop", 0.0) * 100 for e in entries), default=0.0
        )
        noon = min(entries, key=lambda e: abs(
            datetime.fromtimestamp(e["dt"], tz=timezone.utc).hour - 12
        ))
        main = noon["main"]
        return WeatherInfo(
            city=city_name,
            country=country,
            date=target.isoformat(),
            temperature_c=sum(temp) / len(temp),
            feels_like_c=main.get("feels_like", main["temp"]),
            humidity_pct=max(e["main"].get("humidity", 0) for e in entries),
            wind_speed_mps=max(e["wind"].get("speed", 0.0) for e in entries),
            pressure_hpa=main.get("pressure", 0),
            condition=noon["weather"][0]["main"],
            description=noon["weather"][0]["description"],
            rain_pct=round(rain_pct),
            uv_index=None,
        )

    def geocode(self, query: str, limit: int = 5) -> list[CitySuggestion]:
        """Autocomplete city names from the bundled GeoNames dataset."""
        q = query.strip().lower()
        if not q:
            return []
        matches = []
        for name, ascii_name, cc in CITIES:
            lowered = name.lower()
            ascii_lowered = ascii_name.lower()
            if lowered == q or ascii_lowered == q:
                score = 0
            elif lowered.startswith(q) or ascii_lowered.startswith(q):
                score = 1
            elif q in lowered or q in ascii_lowered:
                score = 2
            else:
                continue
            matches.append((score, name, cc))
        matches.sort(key=lambda m: m[0])

        suggestions = []
        for _, name, cc in matches[:limit]:
            country_name = COUNTRY_NAMES.get(cc, cc)
            suggestions.append(
                CitySuggestion(
                    name=name,
                    country=cc,
                    country_name=country_name,
                    label=f"{name}, {country_name}",
                    q=f"{name},{cc}",
                )
            )
        return suggestions
