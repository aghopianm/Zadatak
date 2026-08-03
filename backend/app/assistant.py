from __future__ import annotations

import json

import httpx

from .config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL
from .schemas import AssistantResponse, WeatherInfo


class GroqError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


SYSTEM_PROMPT = (
    "You are a friendly personal weather assistant. Given the weather data for a "
    "city on a specific date, produce practical, personalized recommendations. "
    "Always answer in JSON with exactly these keys: summary, clothing, activities, "
    "precautions. Keep each field to 1-3 sentences. No markdown, no extra text."
)


def _build_user_prompt(weather: WeatherInfo) -> str:
    return (
        f"City: {weather.city}, {weather.country}\n"
        f"Date: {weather.date}\n"
        f"Condition: {weather.condition} ({weather.description})\n"
        f"Temperature: {weather.temperature_c:.1f} C (feels like {weather.feels_like_c:.1f} C)\n"
        f"Humidity: {weather.humidity_pct}%\n"
        f"Wind: {weather.wind_speed_mps:.1f} m/s\n"
        f"Pressure: {weather.pressure_hpa} hPa\n"
        f"Chance of rain: {weather.rain_pct if weather.rain_pct is not None else 'unknown'}%\n"
        "Give recommendations for clothing, outdoor activities, and health precautions."
    )


class GroqAssistant:
    """LLM client that turns weather data into recommendations via Groq."""

    def __init__(self, api_key: str = GROQ_API_KEY, model: str = GROQ_MODEL):
        self.api_key = api_key
        self.model = model

    def recommend(self, weather: WeatherInfo) -> AssistantResponse:
        if not self.api_key:
            raise GroqError("GROQ_API_KEY is not configured.", 500)
        body = {
            "model": self.model,
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(weather)},
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{GROQ_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
        except httpx.HTTPError as exc:
            raise GroqError(f"Groq request failed: {exc}", 502)

        if response.status_code != 200:
            raise GroqError(
                f"Groq API error ({response.status_code}): {response.text[:200]}",
                502,
            )

        content = response.json()["choices"][0]["message"]["content"]
        return self._parse(content)

    def _parse(self, content: str) -> AssistantResponse:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            payload = {"summary": content, "clothing": "", "activities": "", "precautions": ""}
        return AssistantResponse(
            summary=payload.get("summary", ""),
            clothing=payload.get("clothing", ""),
            activities=payload.get("activities", ""),
            precautions=payload.get("precautions", ""),
        )
