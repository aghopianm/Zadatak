from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .assistant import GroqAssistant, GroqError
from .config import GROQ_API_KEY, OPENWEATHER_API_KEY
from .schemas import ErrorResponse, HealthResponse, Recommendation
from .weather import OpenWeatherClient, WeatherError

app = FastAPI(
    title="Personal Weather Assistant",
    description="Combines OpenWeatherMap data with Groq LLM recommendations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Check API configuration",
)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        weather_api_configured=bool(OPENWEATHER_API_KEY),
        groq_api_configured=bool(GROQ_API_KEY),
    )


@app.get(
    "/api/recommendation",
    response_model=Recommendation,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get weather + AI recommendations for a city on a date",
)
def recommendation(
    city: str = Query(..., min_length=1, description="City name, e.g. Zagreb"),
    date: date = Query(..., description="Target date (today or within next 5 days)"),
) -> Recommendation:
    weather_client = OpenWeatherClient()
    assistant = GroqAssistant()
    try:
        weather = weather_client.fetch_weather_for_date(city, date)
    except WeatherError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    try:
        assistant_response = assistant.recommend(weather)
    except GroqError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return Recommendation(weather=weather, assistant=assistant_response)
