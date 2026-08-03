import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CityAutocomplete from './CityAutocomplete'

const suggestions = [
  {
    name: 'Zagreb',
    country: 'HR',
    country_name: 'Croatia',
    label: 'Zagreb, Croatia',
    q: 'Zagreb,HR',
  },
  {
    name: 'Zagazig',
    country: 'EG',
    country_name: 'Egypt',
    label: 'Zagazig, Egypt',
    q: 'Zagazig,EG',
  },
]

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

describe('CityAutocomplete', () => {
  it('fetches suggestions after typing at least 2 characters', async () => {
    const fetchMock = stubFetch(suggestions)
    render(<CityAutocomplete value="" onChange={() => {}} />)

    await userEvent.type(screen.getByRole('textbox'), 'Zag')

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/cities?q=Zag'),
      ),
    )
    expect(await screen.findByText('Zagreb, Croatia')).toBeInTheDocument()
  })

  it('does not fetch for a single character', async () => {
    const fetchMock = stubFetch(suggestions)
    render(<CityAutocomplete value="" onChange={() => {}} />)

    await userEvent.type(screen.getByRole('textbox'), 'Z')

    await new Promise((resolve) => setTimeout(resolve, 400))
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('calls onChange with the q value when a suggestion is selected', async () => {
    stubFetch(suggestions)
    const onChange = vi.fn()
    render(<CityAutocomplete value="" onChange={onChange} />)

    await userEvent.type(screen.getByRole('textbox'), 'Zag')
    await userEvent.click(await screen.findByText('Zagreb, Croatia'))

    expect(onChange).toHaveBeenCalledWith('Zagreb,HR')
  })

  it('closes the dropdown on Escape', async () => {
    stubFetch(suggestions)
    render(<CityAutocomplete value="" onChange={() => {}} />)

    await userEvent.type(screen.getByRole('textbox'), 'Zag')
    await screen.findByText('Zagreb, Croatia')
    await userEvent.keyboard('{Escape}')

    await waitFor(() =>
      expect(screen.queryByText('Zagreb, Croatia')).not.toBeInTheDocument(),
    )
  })
})
