import { describe, expect, it } from 'vitest'
import { mockApi } from '../test/mockApi'
import { api } from './api'

describe('api client', () => {
  it('encodes query parameters', async () => {
    const calls = mockApi({ '/opportunities': [] })
    await api.opportunities.list('seo_content', 'food & drink', true)
    const query = new URLSearchParams(calls[0].query)
    expect(query.get('industry')).toBe('food & drink')
    expect(query.get('opp_type')).toBe('seo_content')
    expect(query.get('demo_only')).toBe('true')
  })

  it('sends JSON bodies with the right method', async () => {
    const calls = mockApi()
    await api.alerts.run('All clients', 70)
    await api.seasonal.updateChannel('c1', 'whatsapp', '+1555')
    expect(calls).toEqual([
      { method: 'POST', path: '/alerts/run', query: '', body: { scope: 'All clients', min_score: 70 } },
      { method: 'PATCH', path: '/clients/channel', query: '', body: { client_id: 'c1', channel: 'whatsapp', whatsapp_number: '+1555' } },
    ])
  })

  it('surfaces the FastAPI detail message on errors', async () => {
    mockApi({ 'POST /pilot/reply': { status: 404, body: { detail: "Proposal 'x' not found." } } })
    await expect(api.pilot.reply('x', 'accepted')).rejects.toThrow("Proposal 'x' not found.")
  })

  it('falls back to status and path when there is no string detail', async () => {
    mockApi({ '/accuracy': { status: 500, body: { detail: [{ msg: 'boom' }] } } })
    await expect(api.accuracy.get()).rejects.toThrow('500 /accuracy')
  })

  it('reads with GET', async () => {
    const calls = mockApi({
      '/follow-ups': [], '/follow-ups/log': [], '/analytics/snapshots': [], '/churn/escalations': [],
      '/crm/sync-log': [], '/seasonal/boosts': [], '/propensity/clients': [], '/whatsapp/log': [],
    })
    await Promise.all([
      api.followUps.list('p1'), api.followUps.log(), api.analytics.snapshots(3), api.churn.escalations(5),
      api.crm.syncLog(2), api.seasonal.boosts(), api.seasonal.propensityClients(), api.seasonal.whatsappLog(),
    ])
    expect(calls.map(c => c.method)).toEqual(Array(8).fill('GET'))
    expect(calls[0].query).toBe('?proposal_id=p1')
  })

  it('writes with a non-GET method', async () => {
    const calls = mockApi()
    await Promise.all([
      api.proposals.generateAll(80), api.proposals.approve('p'), api.proposals.reject('p'),
      api.proposals.updateBody('p', 'b'), api.proposals.revoke('p'), api.pilot.detect('c'),
      api.pilot.generate('c'), api.pilot.send('p', 90, 100, 't'), api.pilot.processAutoQueue(),
      api.ml.train(), api.textSignals.process(true), api.negotiations.kill('p'), api.negotiations.start('p'),
      api.negotiations.tooExpensive('p'), api.paymentLinks.create('p', 10), api.followUps.schedule('p'),
      api.followUps.cancel('f'), api.analytics.snapshot(), api.churn.scan(), api.crm.sync('p', 'c', 1, 't'),
      api.seasonal.updatePropensity(), api.alerts.clear(),
    ])
    expect(calls).toHaveLength(22)
    expect(calls.every(c => c.method !== 'GET')).toBe(true)
  })
})
