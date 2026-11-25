/** Behaviour tests for the interactive pages. */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { mockApi } from '../test/mockApi'
import AlertFeedPage from './AlertFeedPage'
import OpportunitiesPage from './OpportunitiesPage'
import ProposalsPage from './ProposalsPage'
import TextSignalsPage from './TextSignalsPage'

const opportunity = (over: Record<string, unknown> = {}) => ({
  client_id: 'c1', client_name: 'Alpha', industry: 'retail', opportunity_type: 'reactivation',
  label: 'Express Reactivation', score: 90, ml_probability: null, blended_score: 90, suggested_price: 150,
  rationale: 'Inactive', triggered_signals: ['high_days_inactive'], is_demo_scenario: 0,
  propensity_tier: 'high', propensity_score: 0.8, ...over,
})

describe('OpportunitiesPage', () => {
  const rows = [
    opportunity(),
    opportunity({ client_id: 'c2', client_name: 'Beta', score: 65, propensity_tier: 'low', seasonal_boost: 1.18 }),
  ]

  it('filters by propensity locally, without another request', async () => {
    const calls = mockApi({ '/opportunities': rows })
    render(<OpportunitiesPage />)
    await screen.findByText(/Alpha/)
    const before = calls.filter(c => c.path === '/opportunities').length

    fireEvent.change(screen.getByDisplayValue('All Tiers'), { target: { value: 'low' } })

    expect(screen.queryByText(/Alpha/)).toBeNull()
    expect(screen.getByText(/Beta/)).toBeTruthy()
    expect(calls.filter(c => c.path === '/opportunities').length).toBe(before)
  })

  it('refetches when a server-side filter changes', async () => {
    const calls = mockApi({ '/opportunities': rows })
    render(<OpportunitiesPage />)
    await screen.findByText(/Alpha/)
    fireEvent.click(screen.getByRole('checkbox'))
    await waitFor(() => expect(calls.some(c => c.query.includes('demo_only=true'))).toBe(true))
  })

  it('sorts the table view and reports the clicked client', async () => {
    mockApi({ '/opportunities': rows })
    const opened: string[] = []
    render(<OpportunitiesPage onSelectClient={id => opened.push(id)} />)
    await screen.findByText(/Alpha/)
    fireEvent.click(screen.getByRole('button', { name: 'Table' }))

    const names = () => screen.getAllByRole('row').slice(1).map(r => within(r).getAllByRole('cell')[0].textContent)
    expect(names()).toEqual(['Alpha', 'Beta'])
    fireEvent.click(screen.getByRole('columnheader', { name: /^Score/ }))
    expect(names()).toEqual(['Beta', 'Alpha'])

    fireEvent.click(screen.getByText('Beta'))
    expect(opened).toEqual(['c2'])
  })

  it('shows the seasonal calendar on demand', async () => {
    mockApi({ '/seasonal/upcoming': [{ name: 'Summer Launch', date: '2026-07-01', days_away: 5, types: ['seo_content'], current_boost: 1.1 }] })
    render(<OpportunitiesPage />)
    fireEvent.click(screen.getByRole('button', { name: /Seasonal Calendar/ }))
    expect(await screen.findByText('Summer Launch')).toBeTruthy()
  })

  it('explains a failed load', async () => {
    mockApi({ '/opportunities': { status: 500, body: { detail: 'database is locked' } } })
    render(<OpportunitiesPage />)
    expect(await screen.findByText(/database is locked/)).toBeTruthy()
  })
})

describe('ProposalsPage', () => {
  const proposal = (over: Record<string, unknown> = {}) => ({
    id: 'p1', client_id: 'c1', client_name: 'Alpha', industry: 'retail', opportunity_type: 'reactivation',
    label: '', score: 90, suggested_price: 150, status: 'draft', created_at: '2026-01-01',
    subject: 'Hello', body: 'Original body', is_demo_scenario: 0, ...over,
  })
  const overrides = {
    '/proposals': [proposal(), proposal({ id: 'p2', client_name: 'Beta', status: 'approved' })],
    '/proposals/metrics': { p1: { ctr: 0.05, bounce_rate: 0.4, pages_per_session: 2, conversion_rate: 0.01, ad_spend: 900, roas: 3, email_open_rate: 0.2, days_inactive: 9 } },
  }

  it('loads metrics for all cards in a single request', async () => {
    const calls = mockApi(overrides)
    render(<ProposalsPage />)
    expect(await screen.findByText('5.0%')).toBeTruthy()
    expect(calls.filter(c => c.path === '/proposals/metrics')).toHaveLength(1)
    expect(calls.some(c => /\/proposals\/p\d\/metrics/.test(c.path))).toBe(false)
  })

  it('approves, edits, rejects and revokes', async () => {
    const calls = mockApi(overrides)
    render(<ProposalsPage />)
    const sent = (method: string, path: string) =>
      waitFor(() => expect(calls.some(c => c.method === method && c.path === path)).toBe(true))

    fireEvent.click(await screen.findByRole('button', { name: 'Edit' }))
    fireEvent.change(screen.getByDisplayValue('Original body'), { target: { value: 'New body' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await sent('PATCH', '/proposals/p1/body')

    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    await sent('POST', '/proposals/p1/approve')
    fireEvent.click(await screen.findByRole('button', { name: 'Reject' }))
    await sent('POST', '/proposals/p1/reject')
    fireEvent.click(await screen.findByRole('button', { name: 'Revoke Approval' }))
    await sent('POST', '/proposals/p2/revoke')
  })
})

describe('AlertFeedPage', () => {
  it('runs detection and clears the log', async () => {
    const calls = mockApi({ 'POST /alerts/run': { dispatched: 2 } })
    render(<AlertFeedPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Run Now' }))
    expect(await screen.findByText('Dispatched 2 alert(s).')).toBeTruthy()

    fireEvent.click(await screen.findByRole('button', { name: 'Clear Log' }))
    await waitFor(() => expect(calls.some(c => c.method === 'DELETE' && c.path === '/alerts')).toBe(true))
    expect(await screen.findByText(/No alerts yet/)).toBeTruthy()
  })
})

describe('TextSignalsPage churn tab', () => {
  it('shows the signal and date of each escalation', async () => {
    const calls = mockApi({
      '/churn/escalations': [{
        id: 'e1', client_id: 'c1', client_name: 'Alpha', account_manager: 'Dana Reyes',
        churn_signal: 'churn_risk', escalated_at: '2026-03-04T10:00:00',
      }],
    })
    render(<TextSignalsPage />)
    fireEvent.click(await screen.findByRole('button', { name: /Churn Escalations/ }))

    expect(await screen.findByText('churn risk')).toBeTruthy()
    expect(screen.getByText('2026-03-04')).toBeTruthy()
    // the raw log endpoint uses other field names, which left both blank
    expect(calls.some(c => c.path === '/churn/log')).toBe(false)
  })
})
