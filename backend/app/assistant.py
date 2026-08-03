from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from .config import GROQ_API_KEY, GROQ_MODEL
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


def build_messages(weather: WeatherInfo) -> list:
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_build_user_prompt(weather)),
    ]


class GroqAssistant:
    """LLM client that turns weather data into recommendations via LangChain ChatGroq."""

    def __init__(
        self,
        api_key: str = GROQ_API_KEY,
        model: str = GROQ_MODEL,
        llm: ChatGroq | None = None,
    ):
        self.api_key = api_key or ""
        self.model = model
        self._llm = llm  # optional injected instance (used in tests)

    def recommend(self, weather: WeatherInfo) -> AssistantResponse:
        if not self.api_key:
            raise GroqError("GROQ_API_KEY is not configured.", 500)
        llm = self._llm or self._build_llm()
        try:
            response = llm.invoke(build_messages(weather))
        except Exception as exc:
            raise GroqError(f"Groq request failed: {exc}", 502) from exc
        return self._parse(response.content)

    def _build_llm(self) -> ChatGroq:
        return ChatGroq(
            model_name=self.model,
            groq_api_key=self.api_key,
            temperature=0.4,
            model_kwargs={"response_format": {"type": "json_object"}},
        )

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
