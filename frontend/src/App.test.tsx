/** Navigation smoke tests: every page renders with realistic data and no crash. */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'
import { mockApi } from './test/mockApi'

function navigate(group: string, page: string) {
  fireEvent.mouseEnter(screen.getByRole('button', { name: new RegExp(`^${group}`) }).parentElement!)
  fireEvent.click(screen.getByRole('button', { name: page }))
}

function clickIfPresent(label: string) {
  const button = screen.queryAllByRole('button').find(b => b.textContent?.trim().startsWith(label))
  if (button) fireEvent.click(button)
}

const PAGES: [group: string, page: string, endpoint: string, tabs: string[]][] = [
  ['Intelligence', 'Text Signals', '/text-signals/summary', ['Signal Matrix', 'Matrix', 'Urgency', 'Churn']],
  ['Intelligence', 'ML Model', '/ml/status', ['Features', 'Predictions', 'Explain']],
  ['Deal Pipeline', 'Negotiation', '/negotiations/summary', ['Demo', 'Payment', 'History']],
  ['Deal Pipeline', 'Proposals', '/proposals', ['Log', 'Follow-Ups', 'CRM']],
  ['Deal Pipeline', 'Pilot Demo', '/pilot/metrics', ['Pilot Report', 'Report', 'Sent', 'Feedback']],
  ['Analytics', 'ROI Dashboard', '/analytics/summary', []],
  ['Analytics', 'Alert Feed', '/alerts', []],
  ['Analytics', 'Accuracy', '/accuracy', []],
]

describe('App navigation', () => {
  it.each(PAGES)('%s → %s loads its data and renders', async (group, page, endpoint, tabs) => {
    const calls = mockApi()
    render(<App />)
    navigate(group, page)

    await waitFor(() => expect(calls.some(c => c.path === endpoint)).toBe(true))
    await waitFor(() => expect(screen.queryByText(/^Loading/)).toBeNull())
    expect(screen.getAllByRole('heading').length).toBeGreaterThan(0)

    // Walk through the page's tabs so their panels render too
    tabs.forEach(clickIfPresent)
    await waitFor(() => expect(screen.getAllByRole('heading').length).toBeGreaterThan(0))
  })

  it('renders the static overview page in both views', async () => {
    mockApi()
    render(<App />)
    navigate('System', 'Overview')
    await waitFor(() => expect(screen.getAllByRole('heading').length).toBeGreaterThan(1))
    clickIfPresent('Engineering')
    expect(screen.getAllByRole('heading').length).toBeGreaterThan(1)
  })

  it('opens a client from the opportunities list and goes back', async () => {
    const calls = mockApi()
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Table' }))
    fireEvent.click((await screen.findAllByRole('row'))[1])

    await waitFor(() => expect(calls.some(c => c.path.endsWith('/detail'))).toBe(true))
    fireEvent.click(await screen.findByRole('button', { name: '← Opportunities' }))
    expect(await screen.findByText('Total Opportunities')).toBeTruthy()
  })
})
