# Personal Weather Assistant

An app that combines live weather data from the **OpenWeatherMap** API with **Groq** LLM analysis to give personalized recommendations for clothing, activities, and health precautions for a given **city** and **date**.

Backend: **Python + FastAPI**
Frontend: **React + Vite**

## Features

- Input a city and a date
- City autocomplete with a bundled world-cities dataset (type `Zag` → "Zagreb, Croatia"); no extra API calls or rate limits
- Fetches current weather (today) or the day's forecast (next 5 days) from OpenWeatherMap
- Sends the weather data to a Groq LLM (free tier) and receives structured recommendations
- Clean dark-themed web UI; also a REST API you can call from a CLI

> Note: the free OpenWeatherMap tier only provides current weather + a 5-day forecast, so the date must be today or within the next 5 days.

## Project structure

```
Graia/
├── .github/
│   └── workflows/
│       └── ci.yml            # GitHub Actions: backend + frontend tests on push/PR
├── backend/                  # Python FastAPI service
│   ├── app/
│   │   ├── main.py          # FastAPI app + endpoints
│   │   ├── config.py        # env config
│   │   ├── schemas.py       # Pydantic models
│   │   ├── weather.py       # OpenWeatherMap client + city autocomplete
│   │   ├── cities_data.py   # Bundled GeoNames dataset (1989 major cities)
│   │   └── assistant.py     # Groq LLM client (LangChain ChatGroq)
│   ├── tests/               # pytest suite (mocked external APIs)
│   ├── requirements.txt
│   └── .env.example
└── frontend/                # React + Vite web app
    ├── src/
    │   ├── App.jsx
    │   ├── App.test.jsx           # unit tests
    │   ├── CityAutocomplete.jsx   # reusable autocomplete component
    │   ├── CityAutocomplete.test.jsx
    │   └── test/setup.js          # Vitest setup
    └── .env.example
```

## Prerequisites

- Python 3.11+ (recommended; tested with 3.12)
- Node.js 22.22+ (required by Vite 8 / jsdom 30; local dev on Node 26 works)
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

### Frontend tests

```bash
cd frontend
npm test
```

Unit tests (Vitest + Testing Library, jsdom) cover the `App` flow (render, submit → results, error handling) and the `CityAutocomplete` component (debounced fetch, selection, keyboard dismissal). No backend or network needed.

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

### City autocomplete

```bash
curl "http://127.0.0.1:8000/api/cities?q=Zag&limit=5"
```

```json
[
  { "name": "Zagreb", "country": "HR", "country_name": "Croatia",
    "label": "Zagreb, Croatia", "q": "Zagreb,HR" },
  { "name": "Zagazig", "country": "EG", "country_name": "Egypt",
    "label": "Zagazig, Egypt", "q": "Zagazig,EG" }
]
```

The `q` field is the exact value to pass as `city` to `/api/recommendation`.

## Data flow

What the app actually extracts and passes between the two APIs.

### 1. From OpenWeatherMap → `WeatherInfo`

| Field | Source | Notes |
| --- | --- | --- |
| `city`, `country` | response `name` + `sys.country` | |
| `temperature_c` | `main.temp` | for a forecast date: mean of the day's 8 (3-hourly) entries |
| `feels_like_c` | `main.feels_like` | |
| `humidity_pct` | `main.humidity` | forecast: max of the day |
| `wind_speed_mps` | `wind.speed` | forecast: max of the day |
| `pressure_hpa` | `main.pressure` | from the noon-ish entry |
| `condition`, `description` | `weather[0].main` / `weather[0].description` | forecast: from the entry nearest 12:00 |
| `rain_pct` | forecast `pop` × 100 | `null` for current weather (not provided) |
| `uv_index` | — | always `null`; UV data requires the paid One Call API |

### 2. From our app → Groq LLM

A single system prompt ("answer in JSON with exactly: summary, clothing,
activities, precautions") plus a user prompt with the `WeatherInfo` fields above:
city, country, date, condition/description, temp, feels-like, humidity, wind,
pressure, chance of rain. Model params: `temperature=0.4`,
`response_format={"type": "json_object"}`.

### 3. From Groq → `AssistantResponse`

```json
{
  "summary": "A very hot day with clear skies.",
  "clothing": "Wear lightweight, light-colored clothing.",
  "activities": "Outdoor activity in the early morning or evening.",
  "precautions": "Stay hydrated and use sunscreen."
}
```

### What we could extend later

- **Free-tier fields we already receive but currently drop**: `weather[0].icon`
  (OpenWeatherMap weather images), `clouds.all` (cover %), `visibility`,
  `main.temp_min`/`temp_max`, `wind.gust`/`wind.deg`, `rain`/`snow`,
  `sys.sunrise`/`sys.sunset`. All easy to add to `WeatherInfo` and pass to the LLM.
- **Free API we don't call yet**: the [Air Pollution API](https://openweathermap.org/api/air-pollution)
  (`/data/2.5/air_pollution`) for AQI + pollutant concentrations — useful for
  sensitive-user advice.
- **Paid only**: UV index and historical/minutely/hourly data require the One
  Call API; the free tier maxes out at current weather + 5-day forecast.

## Configuration reference

| Variable                | Where       | Description                                  |
| ----------------------- | ----------- | -------------------------------------------- |
| `OPENWEATHERMAP_API_KEY`| `backend/.env` | OpenWeatherMap API key                   |
| `GROQ_API_KEY`          | `backend/.env` | Groq API key                             |
| `VITE_API_BASE`         | `frontend/.env` | Optional override for the backend base URL |

## Future expansion

The LLM layer currently uses LangChain's `ChatGroq` wrapper over a single prompt
(no chains, no agents, no graph). That keeps the flow simple while giving us the
portability and tool-calling options below. When the app grows, these are the
recommended upgrades.

### When to use more of LangChain

- **Tool use / function calling** — if the assistant should ask the user
  follow-up questions, look up more data, or act on the recommendations (e.g.
  "book the best match of these activities"), LangChain's tool-calling support
  handles the orchestration cleanly.
- **Multi-step workflows** — e.g. compare several cities or build a multi-day
  itinerary. LangGraph is the right fit here because each step (fetch weather →
  analyze → plan day N+1) is a node in a stateful graph with its own prompt and
  memory.
- **Model/provider portability** — LangChain's `ChatGroq` gives you the option to
  swap the model provider (OpenAI, Anthropic, local models) without rewriting the
  prompt layer.
- **Streaming conversations** — if you want a chat UI that streams tokens to the
  frontend, LangChain adds streaming abstractions out of the box.

### Where we are and what's next

1. Add LangGraph only when the flow needs state (multi-day planning, follow-up
   questions). Start with a single-node graph wrapping the current logic; add
   nodes later without changing the endpoint.
2. Consider `uv_index` and air-quality data from OpenWeatherMap's One Call API
   (paid tier) for richer advice (sunscreen/UV warnings, AQI for sensitive
   users).
3. Alerting: trigger a push/email when conditions match user preferences
   (e.g. "rain > 50% on my commute").
4. i18n: recommendations in the user's language via the `language` query param.
5. Caching the 5-day forecast per city to stay comfortably under the free-tier
   call limit.

