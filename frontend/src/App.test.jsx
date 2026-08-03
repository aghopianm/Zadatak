import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

const weatherPayload = {
  weather: {
    city: 'Zagreb',
    country: 'HR',
    date: '2026-08-03',
    temperature_c: 38.8,
    feels_like_c: 37.0,
    humidity_pct: 20,
    wind_speed_mps: 1.7,
    pressure_hpa: 1012,
    condition: 'Clear',
    description: 'clear sky',
    rain_pct: 0,
    uv_index: null,
  },
  assistant: {
    summary: 'A very hot day with clear skies.',
    clothing: 'Wear light clothing.',
    activities: 'Stay inside at noon.',
    precautions: 'Drink water.',
  },
}

function stubFetch(body) {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => body })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }))
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('renders the form', () => {
    render(<App />)
    expect(
      screen.getByRole('heading', { name: /personal weather assistant/i }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('City')).toBeInTheDocument()
    expect(screen.getByLabelText('Date')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /get recommendations/i }),
    ).toBeInTheDocument()
  })

  it('fetches and renders recommendations on submit', async () => {
    const fetchMock = stubFetch(weatherPayload)
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: /get recommendations/i }))

    expect(await screen.findByText('38.8°C')).toBeInTheDocument()
    expect(screen.getByText(/a very hot day with clear skies/i)).toBeInTheDocument()
    expect(screen.getByText(/wear light clothing/i)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/recommendation'),
    )
  })

  it('shows an error message when the request fails', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: false, json: async () => ({ detail: 'City not found.' }) })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: /get recommendations/i }))

    expect(await screen.findByText(/city not found/i)).toBeInTheDocument()
  })
})
