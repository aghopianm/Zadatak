from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from app.assistant import GroqAssistant, build_messages
from app.main import app
from app.schemas import WeatherInfo
from app.weather import OpenWeatherClient, WeatherError


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

    def test_get_unauthorized_key(self, monkeypatch):
        class FakeResponse:
            status_code = 401
            text = '{"message": "Invalid API key."}'

        monkeypatch.setattr(httpx.Client, "get", lambda *a, **k: FakeResponse())
        with pytest.raises(WeatherError) as exc:
            OpenWeatherClient(api_key="bad")._get("weather", {"q": "Zagreb"})
        assert exc.value.status_code == 500
        assert "Invalid OpenWeatherMap API key" in str(exc.value)

    def test_get_city_not_found(self, monkeypatch):
        class FakeResponse:
            status_code = 404
            text = '{"message": "city not found"}'

        monkeypatch.setattr(httpx.Client, "get", lambda *a, **k: FakeResponse())
        with pytest.raises(WeatherError) as exc:
            OpenWeatherClient(api_key="ok")._get("weather", {"q": "Nope"})
        assert exc.value.status_code == 404

    def test_get_upstream_error(self, monkeypatch):
        class FakeResponse:
            status_code = 502
            text = "bad gateway"

        monkeypatch.setattr(httpx.Client, "get", lambda *a, **k: FakeResponse())
        with pytest.raises(WeatherError) as exc:
            OpenWeatherClient(api_key="ok")._get("forecast", {"q": "Zagreb"})
        assert exc.value.status_code == 502
        assert "bad gateway" in str(exc.value)

    def test_get_returns_json_on_success(self, monkeypatch):
        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {"cod": 200, "main": {"temp": 20.0}}

        monkeypatch.setattr(httpx.Client, "get", lambda *a, **k: FakeResponse())
        result = OpenWeatherClient(api_key="ok")._get("weather", {"q": "Zagreb"})
        assert result["main"]["temp"] == 20.0

    def test_forecast_date_not_available(self, monkeypatch):
        def fake_get(self, path, params):
            payload = forecast_payload()
            payload["list"] = []
            return payload

        monkeypatch.setattr(OpenWeatherClient, "_get", fake_get)
        client = OpenWeatherClient(api_key="test-key")
        with pytest.raises(WeatherError) as exc:
            client.fetch_weather_for_date("Zagreb", date(2026, 8, 5))
        assert exc.value.status_code == 404
        assert "No forecast data available" in str(exc.value)


class TestGeocode:
    def test_geocode_empty_query(self):
        client = OpenWeatherClient(api_key="test-key")
        assert client.geocode("   ") == []

    def test_geocode_exact_match_first(self):
        client = OpenWeatherClient(api_key="test-key")
        results = client.geocode("Zagreb")
        assert results[0].label == "Zagreb, Croatia"

    def test_geocode_prefix_matching(self):
        client = OpenWeatherClient(api_key="test-key")
        results = client.geocode("Zag")
        assert results[0].label == "Zagreb, Croatia"
        assert results[0].q == "Zagreb,HR"

    def test_geocode_partial_prefix_found(self):
        client = OpenWeatherClient(api_key="test-key")
        labels = [r.label for r in client.geocode("Za", limit=20)]
        assert "Zagreb, Croatia" in labels

    def test_geocode_contains_fallback(self):
        client = OpenWeatherClient(api_key="test-key")
        results = client.geocode("york")
        assert any(r.q == "New York City,US" for r in results)

    def test_cities_endpoint(self, client, monkeypatch):
        monkeypatch.setattr(
            "app.main.OpenWeatherClient.geocode",
            lambda *a, **k: [
                {
                    "name": "Zagreb",
                    "country": "HR",
                    "country_name": "Croatia",
                    "label": "Zagreb, Croatia",
                    "q": "Zagreb,HR",
                }
            ],
        )
        response = client.get("/api/cities", params={"q": "Za"})
        assert response.status_code == 200
        assert response.json()[0]["q"] == "Zagreb,HR"


class TestGroqAssistant:
    def test_parse_handles_json(self):
        assistant = GroqAssistant(api_key="test-key")
        result = assistant._parse(
            '{"summary": "Sunny.", "clothing": "T-shirt", '
            '"activities": "Walk", "precautions": "Sunscreen"}'
        )
        assert result.summary == "Sunny."
        assert result.clothing == "T-shirt"

    def test_missing_key_rejected(self):
        assistant = GroqAssistant(api_key="")
        with pytest.raises(Exception) as exc:
            assistant.recommend(make_weather())
        assert "not configured" in str(exc.value)

    def test_llm_failure_mapped_to_groq_error(self):
        class FailingLLM:
            def invoke(self, messages):
                raise RuntimeError("connection refused")

        assistant = GroqAssistant(api_key="test-key", llm=FailingLLM())
        with pytest.raises(Exception) as exc:
            assistant.recommend(make_weather())
        assert "connection refused" in str(exc.value)
        assert exc.value.status_code == 502

    def test_parse_falls_back_on_non_json(self):
        assistant = GroqAssistant(api_key="test-key")
        result = assistant._parse("Just some plain text reply")
        assert result.summary == "Just some plain text reply"
        assert result.clothing == ""

    def test_langchain_fake_model_end_to_end(self):
        from langchain_core.language_models.fake_chat_models import FakeListChatModel

        fake = FakeListChatModel(
            responses=[
                '{"summary": "Warm.", "clothing": "Light", '
                '"activities": "Cycle", "precautions": "Hydrate"}'
            ]
        )
        assistant = GroqAssistant(api_key="test-key", llm=fake)
        result = assistant.recommend(make_weather())
        assert result.summary == "Warm."
        assert result.activities == "Cycle"

    def test_messages_built_for_weather(self):
        messages = build_messages(make_weather())
        assert "Zagreb" in messages[1].content
        assert messages[0].type == "system"


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

    def test_groq_error_mapped_to_502(self, client, monkeypatch):
        monkeypatch.setattr(
            "app.main.OpenWeatherClient.fetch_weather_for_date",
            lambda *a, **k: make_weather(),
        )

        class _FailingAssistant:
            def recommend(self, weather):
                from app.assistant import GroqError

                raise GroqError("Groq API error (500): boom", 502)

        monkeypatch.setattr("app.main.GroqAssistant", lambda *a, **k: _FailingAssistant())
        response = client.get(
            "/api/recommendation",
            params={"city": "Zagreb", "date": "2026-08-04"},
        )
        assert response.status_code == 502
        assert "boom" in response.json()["detail"]

    def test_cities_endpoint_weather_error(self, client, monkeypatch):
        def _fail(self, q, limit):
            raise WeatherError("Geocoding broken", 502)

        monkeypatch.setattr("app.main.OpenWeatherClient.geocode", _fail)
        response = client.get("/api/cities", params={"q": "Za"})
        assert response.status_code == 502
        assert response.json()["detail"] == "Geocoding broken"
