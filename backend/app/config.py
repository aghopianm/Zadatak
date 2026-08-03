import os

from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

FORECAST_DAYS_LIMIT = 5
