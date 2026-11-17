import { useState, useEffect } from 'react'
import Eyebrow from '../components/Eyebrow'
import { api, type Client, type PilotMetrics } from '../services/api'

const INTENT_LABELS: Record<string, string> = {
  accepted:      'Accepted',
  rejected:      'Rejected',
  too_expensive: 'Too Expensive',
  need_info:     'Needs More Info',
  ignored:       'No Response',
  escalated:     'Escalated',
}

const INTENT_COLORS: Record<string, string> = {
  accepted:      '#27b97c',
  rejected:      '#e03448',
  too_expensive: '#c8982a',
  need_info:     '#336699',
  ignored:       '#6b7280',
  escalated:     '#e03448',
}

const SCENARIOS: Record<string, { description: string; intent: string }> = {
  'Easy Close':      { description: 'High-score opportunity, client accepts immediately.', intent: 'accepted' },
  'Price Objection': { description: 'Client interested but pushes back on price.',           intent: 'too_expensive' },
  'No Reply':        { description: 'Client ignores the proposal for 14 days.',              intent: 'ignored' },
  'Escalation':      { description: 'Client complains and requests human follow-up.',         intent: 'escalated' },
}

const hero: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  backgroundImage: `linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)`,
  backgroundSize: '48px 48px',
  padding: '52px 48px 0',
}
const wrap: React.CSSProperties = { maxWidth: 'var(--max-width-dashboard)', margin: '0 auto' }
const card: React.CSSProperties = { backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', border: '1px solid var(--primary-10)' }

const OPPORTUNITY_LABELS: Record<string, string> = {
  landing_page_optimization: 'Landing Page Optimization',
  seo_content:               'SEO Content Package',
  retargeting_campaign:      'Retargeting Campaign',
  email_automation:          'Email Automation',
  reactivation:              'Express Reactivation',
  conversion_rate_audit:     'Conversion Rate Audit',
  upsell_ad_budget:          'Ad Budget Expansion',
}

type Step = 'idle' | 'detected' | 'generated' | 'sent' | 'replied' | 'done'

interface DetectResult { label: string; opportunity_type: string; score: number; suggested_price: number; rationale: string; tier: string }
interface GenerateResult { proposal_id: string; subject: string; status: string; already_existed: boolean }

export default function PilotPage() {
  const [clients,      setClients]      = useState<Client[]>([])
  const [pilotMetrics, setPilotMetrics] = useState<PilotMetrics | null>(null)
  const [sentLog,      setSentLog]      = useState<Record<string, unknown>[]>([])
  const [feedbackData, setFeedbackData] = useState<{ feedback: Record<string, unknown>[]; calendars: unknown[]; escalations: unknown[] } | null>(null)
  const [loading,      setLoading]      = useState(true)
  const [activeTab,    setActiveTab]    = useState<'Sim' | 'Report' | 'Sent' | 'Feedback'>('Sim')

  // Simulation state
  const [selClient,    setSelClient]    = useState('')
  const [selScenario,  setSelScenario]  = useState(Object.keys(SCENARIOS)[0])
  const [step,         setStep]         = useState<Step>('idle')
  const [opps,         setOpps]         = useState<DetectResult[]>([])
  const [proposal,     setProposal]     = useState<GenerateResult | null>(null)
  const [sendTier,     setSendTier]     = useState<string | null>(null)
  const [feedbackRes,  setFeedbackRes]  = useState<Record<string, unknown> | null>(null)
  const [simMsg,       setSimMsg]       = useState<string | null>(null)
  const [running,      setRunning]      = useState(false)
  const [autoQueue,    setAutoQueue]    = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    Promise.all([api.clients.list(), api.pilot.metrics(), api.pilot.sentLog(), api.pilot.feedbackLog(), api.pilot.autoQueue()])
      .then(([c, m, sl, fl, aq]) => {
        setClients(c)
        setPilotMetrics(m)
        setSentLog(sl)
        setFeedbackData(fl as typeof feedbackData)
        setAutoQueue(aq)
        if (c.length > 0 && !selClient) setSelClient(c[0].id)
      }).finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const run = async (fn: () => Promise<void>) => {
    setRunning(true); setSimMsg(null)
    try { await fn() } catch (e) { setSimMsg(`Error: ${e}`) }
    setRunning(false)
  }

  const detect = () => run(async () => {
    const res = await api.pilot.detect(selClient)
    if (!res.opportunities.length) { setSimMsg('No opportunities detected for this client.'); return }
    setOpps(res.opportunities)
    setStep('detected')
  })

  const generate = () => run(async () => {
    const res = await api.pilot.generate(selClient)
    setProposal(res)
    setStep('generated')
  })

  const send = () => run(async () => {
    if (!proposal || !opps.length) return
    const top = opps[0]
    const res = await api.pilot.send(proposal.proposal_id, top.score, top.suggested_price, top.opportunity_type)
    setSendTier(res.tier)
    setStep('sent')
  })

  const recordReply = () => run(async () => {
    if (!proposal) return
    const intent = SCENARIOS[selScenario].intent
    const res    = await api.pilot.reply(proposal.proposal_id, intent, '', true)
    setFeedbackRes(res as Record<string, unknown>)
    setStep('done')
    // refresh pilot metrics
    api.pilot.metrics().then(setPilotMetrics)
    api.pilot.sentLog().then(setSentLog)
    api.pilot.feedbackLog().then(d => setFeedbackData(d as typeof feedbackData))
  })

  const reset = () => { setStep('idle'); setOpps([]); setProposal(null); setSendTier(null); setFeedbackRes(null); setSimMsg(null) }

  const processQueue = () => run(async () => {
    const res = await api.pilot.processAutoQueue()
    setSimMsg(`Sent ${res.sent} autonomous email(s).`)
    api.pilot.autoQueue().then(setAutoQueue)
  })

  const tabBtn = (t: string): React.CSSProperties => ({
    background: 'none', border: 'none', cursor: 'pointer',
    fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 500, letterSpacing: '1.5px', textTransform: 'uppercase',
    padding: '10px 20px', marginBottom: -1,
    borderBottom: `2px solid ${activeTab === t ? 'var(--gold-light)' : 'transparent'}`,
    color: activeTab === t ? 'var(--gold-light)' : 'rgba(255,255,255,0.4)', transition: 'color 0.15s',
  })

  const kpi = pilotMetrics

  return (
    <div>
      <div style={hero}>
        <div style={wrap}>
          <Eyebrow light>Deal Pipeline</Eyebrow>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: '#fff', margin: '0 0 6px', lineHeight: 1.2 }}>
            Pilot — <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Full Cycle Demo</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'rgba(255,255,255,0.45)', marginBottom: 32 }}>
            Complete agent loop: detect → generate → send → client reply → feedback
          </p>
          {kpi && (
            <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap', marginBottom: 32 }}>
              {[
                { value: String(kpi.total_opportunities),  label: 'Opportunities' },
                { value: String(kpi.proposals_generated),  label: 'Proposals' },
                { value: String(kpi.proposals_sent),       label: 'Sent' },
                { value: String(kpi.proposals_accepted),   label: 'Accepted' },
                { value: `$${kpi.total_revenue.toLocaleString()}`, label: 'Revenue' },
              ].map(s => (
                <div key={s.label} style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18 }}>
                  <div style={{ fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 300, color: 'var(--gold-light)', lineHeight: 1 }}>{s.value}</div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>{s.label}</div>
                </div>
              ))}
            </div>
          )}
          <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
            {(['Sim', 'Report', 'Sent', 'Feedback'] as const).map(t => (
              <button key={t} style={tabBtn(t)} onClick={() => setActiveTab(t)}>
                {t === 'Sim' ? 'Simulation' : t === 'Report' ? 'Pilot Report' : t === 'Sent' ? 'Sent Emails' : 'Feedback Log'}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ backgroundColor: 'var(--light)' }}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto', padding: '44px 48px', display: 'flex', flexDirection: 'column', gap: 32 }}>

          {loading && <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>Loading…</p>}

          {/* ── Simulation ── */}
          {!loading && activeTab === 'Sim' && (
            <section>
              <Eyebrow>Full Cycle Simulation</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
                Step-by-step <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>demo</em>
              </h2>

              {/* Controls */}
              <div style={{ ...card, padding: 24, marginBottom: 24 }}>
                <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginBottom: step !== 'idle' ? 16 : 0 }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>Client</label>
                    <select value={selClient} onChange={e => setSelClient(e.target.value)} disabled={step !== 'idle'}
                      style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#1c1c2e', border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', backgroundColor: '#fff', cursor: 'pointer', width: '100%', colorScheme: 'light' }}>
                      {clients.map(c => <option key={c.id} value={c.id}>{c.name} ({c.industry})</option>)}
                    </select>
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>Demo Scenario</label>
                    <select value={selScenario} onChange={e => setSelScenario(e.target.value)} disabled={step !== 'idle'}
                      style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#1c1c2e', border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', backgroundColor: '#fff', cursor: 'pointer', width: '100%', colorScheme: 'light' }}>
                      {Object.keys(SCENARIOS).map(k => <option key={k} value={k}>{k}</option>)}
                    </select>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginTop: 6 }}>{SCENARIOS[selScenario].description}</div>
                  </div>
                </div>
                {step !== 'idle' && (
                  <button onClick={reset} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', background: 'none', color: 'var(--mid)', border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: '8px 16px', cursor: 'pointer' }}>
                    Reset Simulation
                  </button>
                )}
              </div>

              {simMsg && <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--status-orange)', marginBottom: 16 }}>{simMsg}</div>}

              {/* Step 1: Detect */}
              <StepBlock n={1} title="Detect Opportunity" done={step !== 'idle'}>
                {step === 'idle' && (
                  <button onClick={detect} disabled={running} style={primaryBtn}>{running ? 'Detecting…' : 'Run Detection Engine'}</button>
                )}
                {opps.length > 0 && opps.map((opp, i) => (
                  <div key={i} style={{ ...card, padding: 20, marginTop: 12 }}>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 14, fontWeight: 600, color: 'var(--dark)', marginBottom: 4 }}>
                      {OPPORTUNITY_LABELS[opp.opportunity_type] ?? opp.label}
                    </div>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginBottom: 8 }}>{opp.rationale}</div>
                    <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                      <span style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, color: 'var(--gold)' }}>${opp.suggested_price.toLocaleString()}</span>
                      <span style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700, letterSpacing: '1px', background: 'var(--primary-10)', color: 'var(--primary)', padding: '2px 8px', borderRadius: 'var(--radius-pill)' }}>Score {opp.score.toFixed(0)}</span>
                      <span style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase', background: opp.tier === 'C' ? 'rgba(39,185,124,0.1)' : 'rgba(200,152,42,0.1)', color: opp.tier === 'C' ? '#27b97c' : '#c8982a', padding: '2px 8px', borderRadius: 'var(--radius-pill)' }}>
                        Tier {opp.tier}
                      </span>
                    </div>
                  </div>
                ))}
              </StepBlock>

              {/* Step 2: Generate */}
              {step === 'detected' && (
                <StepBlock n={2} title="Generate Proposal" done={false}>
                  <button onClick={generate} disabled={running} style={primaryBtn}>{running ? 'Generating…' : 'Generate Proposal'}</button>
                </StepBlock>
              )}
              {proposal && step !== 'idle' && step !== 'detected' && (
                <StepBlock n={2} title="Generate Proposal" done>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--status-green)' }}>
                    Proposal {proposal.already_existed ? 'retrieved' : 'generated'} — Subject: {proposal.subject}
                  </div>
                </StepBlock>
              )}

              {/* Step 3: Send */}
              {step === 'generated' && (
                <StepBlock n={3} title="Send Proposal" done={false}>
                  <button onClick={send} disabled={running} style={primaryBtn}>{running ? 'Sending…' : 'Send Proposal'}</button>
                </StepBlock>
              )}
              {sendTier && step !== 'idle' && step !== 'detected' && step !== 'generated' && (
                <StepBlock n={3} title="Send Proposal" done>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--status-green)' }}>
                    Email sent. Tier {sendTier}{sendTier === 'C' ? ' (autonomous)' : ' (approved)'}
                  </div>
                </StepBlock>
              )}

              {/* Step 4: Reply + Feedback */}
              {step === 'sent' && (
                <StepBlock n={4} title="Simulate Client Reply &amp; Record Feedback" done={false}>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginBottom: 12 }}>
                    Scenario: <strong style={{ color: 'var(--dark)' }}>{selScenario}</strong> — Intent: <strong style={{ color: INTENT_COLORS[SCENARIOS[selScenario].intent] ?? 'var(--dark)' }}>{INTENT_LABELS[SCENARIOS[selScenario].intent]}</strong>
                  </div>
                  <button onClick={recordReply} disabled={running} style={primaryBtn}>{running ? 'Processing…' : 'Record Client Reply'}</button>
                </StepBlock>
              )}

              {/* Step 5: Done */}
              {step === 'done' && feedbackRes && (
                <StepBlock n={4} title="Feedback Loop" done>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginTop: 8 }}>
                    {[
                      { label: 'Revenue',        value: `$${((feedbackRes.revenue as number) || 0).toLocaleString()}` },
                      { label: 'Confidence Δ',  value: `${(feedbackRes.confidence_delta as number) >= 0 ? '+' : ''}${feedbackRes.confidence_delta as number} pts`, color: (feedbackRes.confidence_delta as number) >= 0 ? 'var(--status-green)' : 'var(--status-red)' },
                      { label: 'Intent',         value: INTENT_LABELS[SCENARIOS[selScenario].intent], color: INTENT_COLORS[SCENARIOS[selScenario].intent] },
                    ].map(({ label, value, color }) => (
                      <div key={label} style={{ ...card, padding: 16, textAlign: 'center' }}>
                        <div style={{ fontFamily: 'var(--fb)', fontSize: 9, textTransform: 'uppercase', letterSpacing: '2px', color: 'var(--mid)', marginBottom: 4 }}>{label}</div>
                        <div style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: color ?? 'var(--dark)' }}>{value}</div>
                      </div>
                    ))}
                  </div>
                  <button onClick={reset} style={{ ...primaryBtn, marginTop: 16 }}>Run Another Simulation</button>
                </StepBlock>
              )}

              {/* Auto-send queue */}
              {autoQueue && (
                <div style={{ ...card, padding: 24 }}>
                  <Eyebrow>Auto-Send Queue</Eyebrow>
                  <div style={{ display: 'flex', gap: 16, margin: '12px 0', flexWrap: 'wrap' }}>
                    {[
                      { label: 'Pending (Approved)', value: String(autoQueue.approved_pending_send ?? 0) },
                      { label: 'Tier A',              value: String((autoQueue.by_tier as Record<string, number>)?.A ?? 0) },
                      { label: 'Tier B',              value: String((autoQueue.by_tier as Record<string, number>)?.B ?? 0) },
                      { label: 'Tier C (auto)',       value: String((autoQueue.by_tier as Record<string, number>)?.C ?? 0) },
                    ].map(({ label, value }) => (
                      <div key={label} style={{ textAlign: 'center' }}>
                        <div style={{ fontFamily: 'var(--fd)', fontSize: 24, fontWeight: 300, color: 'var(--dark)' }}>{value}</div>
                        <div style={{ fontFamily: 'var(--fb)', fontSize: 9, textTransform: 'uppercase', letterSpacing: '2px', color: 'var(--mid)', marginTop: 4 }}>{label}</div>
                      </div>
                    ))}
                  </div>
                  {((autoQueue.by_tier as Record<string, number>)?.C ?? 0) > 0 && (
                    <button onClick={processQueue} disabled={running} style={primaryBtn}>{running ? 'Processing…' : 'Process Tier C Queue Now'}</button>
                  )}
                </div>
              )}
            </section>
          )}

          {/* ── Pilot Report ── */}
          {!loading && activeTab === 'Report' && kpi && (
            <section>
              <Eyebrow>Pilot Report</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
                Aggregated <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>metrics</em>
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16, marginBottom: 24 }}>
                {[
                  { label: 'Opportunities',    value: String(kpi.total_opportunities) },
                  { label: 'Proposals',        value: String(kpi.proposals_generated) },
                  { label: 'Sent',             value: String(kpi.proposals_sent) },
                  { label: `Accepted (${kpi.acceptance_rate_pct}%)`, value: String(kpi.proposals_accepted) },
                  { label: 'Revenue',          value: `$${kpi.total_revenue.toLocaleString()}` },
                ].map(({ label, value }) => (
                  <div key={label} style={{ ...card, padding: 24, display: 'flex', alignItems: 'stretch', gap: 12 }}>
                    <div style={{ width: 3, backgroundColor: 'var(--gold)', borderRadius: 2, flexShrink: 0 }} />
                    <div>
                      <div style={{ fontFamily: 'var(--fd)', fontSize: 24, fontWeight: 300, color: 'var(--dark)' }}>{value}</div>
                      <div style={{ fontFamily: 'var(--fb)', fontSize: 9, textTransform: 'uppercase', letterSpacing: '2px', color: 'var(--mid)', marginTop: 4 }}>{label}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16 }}>
                {[
                  { label: 'Escalations',        value: String(kpi.escalations) },
                  { label: 'Rejections',          value: String(kpi.proposals_rejected) },
                  { label: `Time Saved (${kpi.time_saved_hours}h est.)`, value: `${kpi.time_saved_hours}h` },
                  { label: 'Autonomous Sends',   value: String(kpi.autonomous_sent) },
                  { label: 'Approval Rate',       value: kpi.proposals_generated ? `${kpi.approved_sent}/${kpi.proposals_generated}` : '—' },
                ].map(({ label, value }) => (
                  <div key={label} style={{ ...card, padding: 20 }}>
                    <div style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)' }}>{value}</div>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 9, textTransform: 'uppercase', letterSpacing: '2px', color: 'var(--mid)', marginTop: 4 }}>{label}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* ── Sent Log ── */}
          {!loading && activeTab === 'Sent' && (
            <section>
              <Eyebrow>Sent Email Log</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
                Dispatched <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>emails</em>
              </h2>
              {sentLog.length === 0 ? (
                <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>No emails sent yet. Run the simulation above.</p>
              ) : sentLog.map((entry, i) => {
                const modeColor = (entry.send_mode as string) === 'autonomous' ? '#27b97c' : '#c8982a'
                return (
                  <div key={i} style={{ ...card, padding: '10px 16px', marginBottom: 8 }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 2fr 1fr 1fr', gap: '4px 12px' }}>
                      <div>
                        <div style={{ fontFamily: 'var(--fb)', fontSize: 9, textTransform: 'uppercase', letterSpacing: '2px', color: 'var(--mid)' }}>Client</div>
                        <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 500, color: 'var(--dark)' }}>{entry.client_name as string}</div>
                      </div>
                      <div>
                        <div style={{ fontFamily: 'var(--fb)', fontSize: 9, textTransform: 'uppercase', letterSpacing: '2px', color: 'var(--mid)' }}>Subject</div>
                        <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--primary-60)' }}>{((entry.subject as string) || '').slice(0, 50)}…</div>
                      </div>
                      <div>
                        <div style={{ fontFamily: 'var(--fb)', fontSize: 9, textTransform: 'uppercase', letterSpacing: '2px', color: 'var(--mid)' }}>Mode</div>
                        <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: modeColor }}>{(entry.send_mode as string || '').toUpperCase()}</div>
                      </div>
                      <div>
                        <div style={{ fontFamily: 'var(--fb)', fontSize: 9, textTransform: 'uppercase', letterSpacing: '2px', color: 'var(--mid)' }}>Time</div>
                        <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{(entry.timestamp as string || '').slice(0, 16).replace('T', ' ')}</div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </section>
          )}

          {/* ── Feedback Log ── */}
          {!loading && activeTab === 'Feedback' && feedbackData && (
            <section>
              <Eyebrow>Feedback &amp; Outcome Log</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
                Client <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>responses</em>
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
                {[
                  { label: 'Feedback Entries',   value: String(feedbackData.feedback.length) },
                  { label: 'Meetings Scheduled', value: String(feedbackData.calendars.length) },
                  { label: 'Escalations',        value: String(feedbackData.escalations.length) },
                ].map(({ label, value }) => (
                  <div key={label} style={{ ...card, padding: 20, display: 'flex', alignItems: 'stretch', gap: 12 }}>
                    <div style={{ width: 3, backgroundColor: 'var(--gold)', borderRadius: 2, flexShrink: 0 }} />
                    <div>
                      <div style={{ fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 300, color: 'var(--dark)' }}>{value}</div>
                      <div style={{ fontFamily: 'var(--fb)', fontSize: 9, textTransform: 'uppercase', letterSpacing: '2px', color: 'var(--mid)', marginTop: 4 }}>{label}</div>
                    </div>
                  </div>
                ))}
              </div>
              {feedbackData.feedback.length === 0 ? (
                <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>No feedback recorded yet. Run the simulation above.</p>
              ) : feedbackData.feedback.map((entry, i) => {
                const intent    = entry.intent as string
                const color     = INTENT_COLORS[intent] ?? '#888'
                const delta     = (entry.confidence_delta as number) || 0
                const deltaStr  = delta !== 0 ? `${delta >= 0 ? '+' : ''}${delta.toFixed(0)}` : '0'
                return (
                  <div key={i} style={{ borderLeft: `3px solid ${color}`, background: 'var(--white)', border: '1px solid var(--primary-10)', padding: '8px 14px', margin: '4px 0', borderRadius: 6, display: 'flex', alignItems: 'center', gap: 10, fontFamily: 'var(--fb)' }}>
                    <span style={{ color, fontWeight: 700, fontSize: '0.82em', textTransform: 'uppercase', letterSpacing: '0.5px', minWidth: 100 }}>{INTENT_LABELS[intent] ?? intent}</span>
                    <span style={{ color: 'var(--dark)', fontSize: '0.85em', fontWeight: 500 }}>{entry.client_name as string}</span>
                    <span style={{ color: 'var(--primary-30)', fontSize: '0.8em' }}>·</span>
                    <span style={{ color: 'var(--mid)', fontSize: '0.8em' }}>Δ {deltaStr} pts</span>
                    <span style={{ color: 'var(--primary-30)', fontSize: '0.8em' }}>·</span>
                    <span style={{ color: 'var(--gold)', fontSize: '0.8em', fontFamily: 'var(--fd)' }}>${((entry.revenue as number) || 0).toLocaleString()}</span>
                  </div>
                )
              })}
            </section>
          )}
        </div>
      </div>
    </div>
  )
}

function StepBlock({ n, title, done, children }: { n: number; title: string; done: boolean; children: React.ReactNode }) {
  return (
    <div style={{ border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-md)', padding: 24, background: done ? 'rgba(39,185,124,0.02)' : 'var(--white)', marginBottom: 16, borderLeft: `3px solid ${done ? 'var(--status-green)' : 'var(--gold)'}` }}>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 600, color: done ? '#27b97c' : 'var(--dark)', marginBottom: 12 }}>
        {done ? '✓' : n + '.'} &nbsp;<span dangerouslySetInnerHTML={{ __html: title }} />
      </div>
      {children}
    </div>
  )
}

const primaryBtn: React.CSSProperties = {
  fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px',
  textTransform: 'uppercase', backgroundColor: 'var(--gold)', color: '#fff',
  border: 'none', borderRadius: 'var(--radius-sm)', padding: '10px 24px', cursor: 'pointer',
}
