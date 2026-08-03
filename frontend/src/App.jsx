import { useState } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE || ''

const DEFAULT_DATE = new Date().toISOString().slice(0, 10)
const MAX_DATE = new Date(Date.now() + 5 * 24 * 60 * 60 * 1000)
  .toISOString()
  .slice(0, 10)

function App() {
  const [city, setCity] = useState('Zagreb')
  const [date, setDate] = useState(DEFAULT_DATE)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function fetchRecommendation(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setData(null)
    try {
      const params = new URLSearchParams({ city, date })
      const response = await fetch(`${API_BASE}/api/recommendation?${params}`)
      const body = await response.json()
      if (!response.ok) {
        throw new Error(body.detail || `Request failed (${response.status})`)
      }
      setData(body)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <header className="header">
        <div className="logo">🌤️</div>
        <div>
          <h1>Personal Weather Assistant</h1>
          <p className="subtitle">
            Weather from OpenWeatherMap, recommendations from Groq AI
          </p>
        </div>
      </header>

      <form className="form" onSubmit={fetchRecommendation}>
        <label>
          City
          <input
            type="text"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="e.g. Zagreb"
            required
          />
        </label>
        <label>
          Date
          <input
            type="date"
            value={date}
            min={DEFAULT_DATE}
            max={MAX_DATE}
            onChange={(e) => setDate(e.target.value)}
            required
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? 'Analyzing…' : 'Get recommendations'}
        </button>
      </form>

      <small className="hint">
        Date must be today or within the next 5 days (free OpenWeatherMap tier).
      </small>

      {error && <div className="error">⚠️ {error}</div>}

      {data && (
        <div className="results">
          <section className="card weather">
            <h2>
              {data.weather.city}, {data.weather.country}
            </h2>
            <p className="date">{data.weather.date}</p>
            <div className="temp">
              {data.weather.temperature_c.toFixed(1)}°C
            </div>
            <p className="condition">
              {data.weather.condition} — {data.weather.description}
            </p>
            <ul className="metrics">
              <li>Feels like: {data.weather.feels_like_c.toFixed(1)}°C</li>
              <li>Humidity: {data.weather.humidity_pct}%</li>
              <li>Wind: {data.weather.wind_speed_mps.toFixed(1)} m/s</li>
              <li>Pressure: {data.weather.pressure_hpa} hPa</li>
              {data.weather.rain_pct !== null && (
                <li>Chance of rain: {data.weather.rain_pct}%</li>
              )}
            </ul>
          </section>

          <section className="card ai">
            <h2>✨ AI Recommendations</h2>
            <div className="ai-block">
              <h3>Summary</h3>
              <p>{data.assistant.summary}</p>
            </div>
            <div className="ai-block">
              <h3>👕 Clothing</h3>
              <p>{data.assistant.clothing}</p>
            </div>
            <div className="ai-block">
              <h3>🚴 Activities</h3>
              <p>{data.assistant.activities}</p>
            </div>
            <div className="ai-block">
              <h3>🩺 Precautions</h3>
              <p>{data.assistant.precautions}</p>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default App
