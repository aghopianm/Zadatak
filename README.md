# Personal Weather Assistant

An app that combines live weather data from the **OpenWeatherMap** API with **Groq** LLM analysis to give personalized recommendations for clothing, activities, and health precautions for a given **city** and **date**.

Backend: **Python + FastAPI**
Frontend: **React + Vite**

## Features

- Input a city and a date
- Fetches current weather (today) or the day's forecast (next 5 days) from OpenWeatherMap
- Sends the weather data to a Groq LLM (free tier) and receives structured recommendations
- Clean dark-themed web UI; also a REST API you can call from a CLI

> Note: the free OpenWeatherMap tier only provides current weather + a 5-day forecast, so the date must be today or within the next 5 days.

## Project structure

```
Graia/
├── backend/                 # Python FastAPI service
│   ├── app/
│   │   ├── main.py          # FastAPI app + endpoints
│   │   ├── config.py        # env config
│   │   ├── schemas.py       # Pydantic models
│   │   ├── weather.py       # OpenWeatherMap client
│   │   └── assistant.py     # Groq LLM client
│   ├── tests/               # pytest suite (mocked external APIs)
│   ├── requirements.txt
│   └── .env.example
└── frontend/                # React + Vite web app
    ├── src/App.jsx
    └── .env.example
```

## Prerequisites

- Python 3.11+ (recommended; tested with 3.12)
- Node.js 18+
- Free API keys:
  - [OpenWeatherMap](https://home.openweathermap.org/api_keys) (up to 1000 calls/day)
  - [Groq](https://console.groq.com/keys) (free tier)

## Backend setup

```bash
cd backend

# 1) Create virtualenv and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2) Configure API keys
cp .env.example .env
#   edit .env and fill in OPENWEATHERMAP_API_KEY and GROQ_API_KEY

# 3) Run the server (http://127.0.0.1:8000)
uvicorn app.main:app --reload
```

Interactive API docs: http://127.0.0.1:8000/docs

### Run the tests

```bash
cd backend
pytest -q
```

The tests mock both external APIs, so they run without keys.

## Frontend setup

```bash
cd frontend

npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` requests to the backend on port 8000, so no extra configuration is needed.

## Usage

### Web UI

1. Start the backend and the frontend (commands above).
2. Open http://localhost:5173.
3. Enter a city (e.g. `Zagreb`) and a date (today or within the next 5 days), then click **Get recommendations**.

### REST API / CLI

```bash
curl "http://127.0.0.1:8000/api/recommendation?city=Zagreb&date=2026-08-04"
```

Example response:

```json
{
  "weather": {
    "city": "Zagreb",
    "country": "HR",
    "date": "2026-08-04",
    "temperature_c": 27.1,
    "feels_like_c": 28.0,
    "humidity_pct": 52,
    "wind_speed_mps": 3.1,
    "pressure_hpa": 1014,
    "condition": "Clear",
    "description": "clear sky",
    "rain_pct": 0
  },
  "assistant": {
    "summary": "A warm, sunny day across Zagreb.",
    "clothing": "Light summer clothing, sunglasses and a hat.",
    "activities": "Great for outdoor sports, cycling or a picnic.",
    "precautions": "Drink plenty of water and use sunscreen."
  }
}
```

### Health check

```bash
curl "http://127.0.0.1:8000/api/health"
```

## Configuration reference

| Variable                | Where       | Description                                  |
| ----------------------- | ----------- | -------------------------------------------- |
| `OPENWEATHERMAP_API_KEY`| `backend/.env` | OpenWeatherMap API key                   |
| `GROQ_API_KEY`          | `backend/.env` | Groq API key                             |
| `GROQ_MODEL`            | `backend/.env` | Groq model id (default `llama-3.3-70b-versatile`) |
| `VITE_API_BASE`         | `frontend/.env` | Optional override for the backend base URL |
