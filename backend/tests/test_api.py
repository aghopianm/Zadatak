from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import WeatherInfo
from app.weather import OpenWeatherClient


@pytest.fixture
def client():
    return TestClient(app)


def make_weather():
    return WeatherInfo(
        city="Zagreb",
        country="HR",
        date="2026-08-04",
        temperature_c=24.5,
        feels_like_c=25.0,
        humidity_pct=60,
        wind_speed_mps=3.2,
        pressure_hpa=1013,
        condition="Clear",
        description="clear sky",
        rain_pct=5,
        uv_index=None,
    )


CURRENT_PAYLOAD = {
    "name": "Zagreb",
    "sys": {"country": "HR"},
    "main": {
        "temp": 24.5,
        "feels_like": 25.0,
        "humidity": 60,
        "pressure": 1013,
    },
    "wind": {"speed": 3.2},
    "weather": [{"main": "Clear", "description": "clear sky"}],
}


def forecast_payload(city="Zagreb", country="HR", days=5):
    entries = []
    base = (date(2026, 8, 4) + timedelta(days=1)).isoformat()
    for hour in (6, 12, 18):
        entries.append(
            {
                "dt": int(
                    datetime.fromisoformat(f"{base}T{hour:02d}:00:00")
                    .replace(tzinfo=timezone.utc)
                    .timestamp()
                ),
                "main": {
                    "temp": 22.0,
                    "feels_like": 21.5,
                    "humidity": 55,
                    "pressure": 1010,
                },
                "wind": {"speed": 2.1},
                "weather": [{"main": "Clouds", "description": "broken clouds"}],
                "pop": 0.3,
            }
        )
    return {
        "city": {"name": city, "country": country},
        "list": entries,
    }


class TestWeatherClient:
    def test_today_uses_current_weather(self, monkeypatch):
        captured = {}

        def fake_get(self, path, params):
            captured["path"] = path
            captured["params"] = params
            return CURRENT_PAYLOAD

        monkeypatch.setattr(OpenWeatherClient, "_get", fake_get)
        client = OpenWeatherClient(api_key="test-key")
        weather = client.fetch_weather_for_date("Zagreb", date.today())
        assert captured["path"] == "weather"
        assert weather.temperature_c == 24.5
        assert weather.condition == "Clear"

    def test_forecast_day_aggregates_entries(self, monkeypatch):
        def fake_get(self, path, params):
            return forecast_payload()

        monkeypatch.setattr(OpenWeatherClient, "_get", fake_get)
        client = OpenWeatherClient(api_key="test-key")
        weather = client.fetch_weather_for_date("Zagreb", date(2026, 8, 5))
        assert weather.temperature_c == 22.0
        assert weather.rain_pct == 30
        assert weather.date == "2026-08-05"

    def test_historical_date_rejected(self, monkeypatch):
        def fake_get(path, params):
            return forecast_payload()

        monkeypatch.setattr(OpenWeatherClient, "_get", fake_get)
        client = OpenWeatherClient(api_key="test-key")
        with pytest.raises(Exception):
            client.fetch_weather_for_date("Zagreb", date(2020, 1, 1))

    def test_missing_api_key(self):
        client = OpenWeatherClient(api_key="")
        with pytest.raises(Exception) as exc:
            client.fetch_weather_for_date("Zagreb", date.today())
        assert "not configured" in str(exc.value)


class TestRecommendationEndpoint:
    def test_health_reports_config(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["weather_api_configured"] in (True, False)
        assert body["groq_api_configured"] in (True, False)

    def test_city_not_found(self, client, monkeypatch):
        class _Fake:
            def fetch_weather_for_date(self, city, date):
                from app.weather import WeatherError

                raise WeatherError("City not found.", 404)

        monkeypatch.setattr("app.main.OpenWeatherClient", lambda *a, **k: _Fake())
        response = client.get("/api/recommendation", params={"city": "Nope", "date": "2026-08-04"})
        assert response.status_code == 404
        assert response.json()["detail"] == "City not found."

    def test_full_flow_with_mocks(self, client, monkeypatch):
        monkeypatch.setattr(
            "app.main.OpenWeatherClient.fetch_weather_for_date",
            lambda *a, **k: make_weather(),
        )
        monkeypatch.setattr(
            "app.main.GroqAssistant.recommend",
            lambda *a, **k: {
                "summary": "Sunny and mild.",
                "clothing": "Light layers.",
                "activities": "Hiking.",
                "precautions": "Wear sunscreen.",
            },
        )
        response = client.get(
            "/api/recommendation",
            params={"city": "Zagreb", "date": "2026-08-04"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["weather"]["city"] == "Zagreb"
        assert body["assistant"]["summary"] == "Sunny and mild."
