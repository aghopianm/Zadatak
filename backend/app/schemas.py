from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WeatherInfo(BaseModel):
    city: str
    country: str
    date: str
    temperature_c: float
    feels_like_c: float
    humidity_pct: int
    wind_speed_mps: float
    pressure_hpa: int
    condition: str
    description: str
    rain_pct: int | None = None
    uv_index: float | None = None


class AssistantResponse(BaseModel):
    summary: str = Field(description="Short overall weather summary for the day")
    clothing: str = Field(description="Clothing recommendations")
    activities: str = Field(description="Activity recommendations")
    precautions: str = Field(description="Health/safety precautions")


class Recommendation(BaseModel):
    weather: WeatherInfo
    assistant: AssistantResponse


class HealthResponse(BaseModel):
    status: str
    weather_api_configured: bool
    groq_api_configured: bool


class ErrorResponse(BaseModel):
    detail: str
