import { useState, useEffect } from 'react'
import Eyebrow from '../components/Eyebrow'
import { api, type NegotiationSummary, type NegotiationTurn } from '../services/api'

const OPPORTUNITY_LABELS: Record<string, string> = {
  landing_page_optimization: 'Landing Page Optimization',
  seo_content:               'SEO Content Package',
  retargeting_campaign:      'Retargeting Campaign',
  email_automation:          'Email Automation',
  reactivation:              'Express Reactivation',
  conversion_rate_audit:     'Conversion Rate Audit',
  upsell_ad_budget:          'Ad Budget Expansion',
}

const SIM_REPLIES: Record<string, string> = {
  'Accepts offer (Turn 1)':       'Perfect, I accept. Let\'s proceed with the offered discount.',
  'Asks for more discount':       'Thank you, but could we possibly get a bit more off?',
  'Rejects definitively':         'I\'m sorry, we\'re not interested at this time.',
  'Ignores — no clear response':  'Hmm, let me think about it and I\'ll get back to you.',
  'Asks to speak with a person':  'Please stop the automated emails, I\'d like to speak with someone.',
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

function ThreadMessage({ turn }: { turn: NegotiationTurn }) {
  const isAgent = turn.role === 'agent'
  // OPB token-aligned tints: agent = primary-10 (light navy), client = very light gold
  const bg     = isAgent ? 'var(--primary-10)' : 'rgba(200,152,42,0.06)'
  const border = isAgent ? 'var(--primary)'    : 'var(--gold)'
  const color  = isAgent ? 'var(--primary)'    : 'var(--gold)'
  const label  = isAgent ? 'Agent' : 'Client'
  const ts     = (turn.timestamp || '').slice(0, 16).replace('T', ' ')

  return (
    <div style={{ background: bg, borderRadius: 8, padding: '10px 14px', margin: '6px 0', borderLeft: `3px solid ${border}`, fontFamily: 'var(--fb)' }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.8px', textTransform: 'uppercase', color, marginBottom: 4 }}>
        {label}&nbsp;&nbsp;
        <span style={{ fontWeight: 400, color: 'var(--mid)', textTransform: 'none', letterSpacing: 0 }}>
          {ts}{turn.offer_price ? ` · Offer: $${turn.offer_price.toLocaleString()}` : ''}
          {turn.intent ? ` · ${turn.intent}` : ''}
        </span>
      </div>
      <div style={{ fontSize: 13, color: 'var(--dark)', lineHeight: 1.6 }}>
        {(turn.message || '').slice(0, 400)}{(turn.message || '').length > 400 ? '…' : ''}
      </div>
    </div>
  )
}

function ActiveNegotiation({ neg, onRefresh }: { neg: Record<string, unknown>; onRefresh: () => void }) {
  const pid    = neg.proposal_id as string
  const [thread, setThread]   = useState<NegotiationTurn[]>([])
  const [reply,  setReply]    = useState('')
  const [msg,    setMsg]      = useState<string | null>(null)

  useEffect(() => {
    api.negotiations.thread(pid).then(setThread)
  }, [pid])

  const submitReply = async () => {
    if (!reply.trim()) return
    const res = await api.negotiations.reply(pid, reply.trim(), false)
    setMsg(`Intent: ${res.intent as string} | Status: ${res.status as string}`)
    setReply('')
    api.negotiations.thread(pid).then(setThread)
    onRefresh()
  }

  const kill = async () => {
    await api.negotiations.kill(pid)
    setMsg('Escalated to account manager.')
    onRefresh()
  }

  return (
    <div style={{ ...card, padding: 24, marginBottom: 16 }}>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 14, fontWeight: 600, color: 'var(--dark)', marginBottom: 4 }}>
        {neg.client_name as string} — {(neg.opportunity_type as string).replace(/_/g, ' ')}
      </div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginBottom: 12 }}>
        Score: {(neg.score as number || 0).toFixed(0)} · Price: ${(neg.suggested_price as number || 0).toLocaleString()} · Turn {neg.turn_count as number} · Last: {(neg.last_activity as string || '').slice(0, 10)}
      </div>

      {thread.map((t, i) => <ThreadMessage key={i} turn={t} />)}

      <div style={{ marginTop: 16, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <textarea
          value={reply}
          onChange={e => setReply(e.target.value)}
          rows={2}
          placeholder="Simulate client reply…"
          style={{ flex: 1, fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', minWidth: 200, resize: 'vertical' }}
        />
        <button onClick={submitReply} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', backgroundColor: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', padding: '10px 16px', cursor: 'pointer' }}>
          Submit Reply
        </button>
        <button onClick={kill} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', background: 'none', color: 'var(--status-red)', border: '1px solid var(--status-red-bg)', borderRadius: 'var(--radius-sm)', padding: '10px 16px', cursor: 'pointer' }}>
          Kill Switch
        </button>
      </div>
      {msg && <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--status-green)', marginTop: 8 }}>{msg}</div>}
    </div>
  )
}

export default function NegotiationPage() {
  const [summary,   setSummary]   = useState<NegotiationSummary | null>(null)
  const [active,    setActive]    = useState<Record<string, unknown>[]>([])
  const [proposals, setProposals] = useState<Record<string, unknown>[]>([])
  const [payLinks,  setPayLinks]  = useState<Record<string, unknown>[]>([])
  const [history,   setHistory]   = useState<Record<string, unknown>[]>([])
  const [loading,   setLoading]   = useState(true)
  const [activeTab, setActiveTab] = useState<'Active' | 'Demo' | 'Payments' | 'History'>('Active')

  // Demo panel state
  const [selPid,      setSelPid]      = useState('')
  const [demoThread,  setDemoThread]  = useState<NegotiationTurn[]>([])
  const [simChoice,   setSimChoice]   = useState(Object.keys(SIM_REPLIES)[0])
  const [demoMsg,     setDemoMsg]     = useState<string | null>(null)
  const [payPid,      setPayPid]      = useState('')
  const [payAmount,   setPayAmount]   = useState(0)
  const [payMsg,      setPayMsg]      = useState<string | null>(null)

  const reload = () => {
    setLoading(true)
    Promise.all([
      api.negotiations.summary(),
      api.negotiations.active(),
      api.proposals.list(),
      api.paymentLinks.list(),
      api.negotiations.history(),
    ]).then(([s, a, p, pl, h]) => {
      setSummary(s)
      setActive(a)
      setProposals(p as unknown as Record<string, unknown>[])
      setPayLinks(pl)
      setHistory(h)
      const sentProps = p.filter((pr: unknown) => ['sent', 'draft', 'approved', 'rejected'].includes((pr as unknown as Record<string, unknown>).status as string))
      if (sentProps.length > 0 && !selPid) setSelPid((sentProps[0] as unknown as Record<string, unknown>).id as string)
    }).finally(() => setLoading(false))
  }

  useEffect(() => { reload() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!selPid) return
    api.negotiations.thread(selPid).then(setDemoThread)
  }, [selPid])

  const triggerTooExpensive = async () => {
    setDemoMsg(null)
    const res = await api.negotiations.tooExpensive(selPid)
    setDemoMsg(`Negotiation opened (${res.method as string}). Check Active tab.`)
    api.negotiations.thread(selPid).then(setDemoThread)
    reload()
  }

  const sendSimReply = async () => {
    setDemoMsg(null)
    const text = SIM_REPLIES[simChoice]
    const res  = await api.negotiations.reply(selPid, text, true)
    setDemoMsg(`Intent: ${res.intent as string} | Status: ${res.status as string}`)
    if ((res.status as string) === 'accepted' && res.offer_price) {
      setDemoMsg(prev => `${prev} · Payment link: generating…`)
      const link = await api.paymentLinks.create(selPid)
      setDemoMsg(prev => `${prev?.replace('generating…', '')} ${link.url}`)
    }
    api.negotiations.thread(selPid).then(setDemoThread)
    reload()
  }

  const generateLink = async () => {
    setPayMsg(null)
    const res = await api.paymentLinks.create(payPid, payAmount || undefined)
    setPayMsg(`Link: ${res.url}`)
    reload()
  }

  const tabBtn = (t: string): React.CSSProperties => ({
    background: 'none', border: 'none', cursor: 'pointer',
    fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 500, letterSpacing: '1.5px', textTransform: 'uppercase',
    padding: '10px 20px', marginBottom: -1,
    borderBottom: `2px solid ${activeTab === t ? 'var(--gold-light)' : 'transparent'}`,
    color: activeTab === t ? 'var(--gold-light)' : 'rgba(255,255,255,0.4)', transition: 'color 0.15s',
  })

  const th: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', padding: '11px 14px', color: '#fff', background: 'var(--primary)', textAlign: 'left' }
  const td: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 14px', color: 'var(--dark)' }

  const sentProposals = proposals.filter(p => ['sent', 'draft', 'approved', 'rejected'].includes(p.status as string))
  const acceptedNoLink = proposals.filter(p => ['accepted', 'sent', 'approved'].includes(p.status as string) && !payLinks.find(l => l.proposal_id === p.id))

  return (
    <div>
      <div style={{ ...hero }}>
        <div style={wrap}>
          <Eyebrow light>Deal Pipeline</Eyebrow>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: '#fff', margin: '0 0 6px', lineHeight: 1.2 }}>
            Autonomous <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Negotiation</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'rgba(255,255,255,0.45)', marginBottom: 32 }}>
            The agent negotiates price with clients over multiple turns using LLM · Stripe closes the deal
          </p>
          {summary && (
            <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap', marginBottom: 32 }}>
              {[
                { value: String(summary.total_negotiations), label: 'Total Negotiations' },
                { value: String(summary.active),             label: 'Active' },
                { value: String(summary.accepted),           label: 'Auto-Resolved' },
                { value: String(summary.rejected),           label: 'Rejected' },
                { value: String(summary.escalated),          label: 'Escalated' },
              ].map(s => (
                <div key={s.label} style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18 }}>
                  <div style={{ fontFamily: 'var(--fd)', fontSize: 32, fontWeight: 300, color: 'var(--gold-light)', lineHeight: 1 }}>{s.value}</div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>{s.label}</div>
                </div>
              ))}
            </div>
          )}
          <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid rgba(255,255,255,0.1)', marginTop: 8 }}>
            {(['Active', 'Demo', 'Payments', 'History'] as const).map(t => (
              <button key={t} style={tabBtn(t)} onClick={() => setActiveTab(t)}>{t === 'Active' ? 'Active Negotiations' : t === 'Demo' ? 'Demo Simulation' : t === 'Payments' ? 'Payment Links' : 'History'}</button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ backgroundColor: 'var(--light)' }}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto', padding: '44px 48px', display: 'flex', flexDirection: 'column', gap: 32 }}>

          {loading && <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>Loading…</p>}

          {/* Active Negotiations */}
          {!loading && activeTab === 'Active' && (
            <section>
              <Eyebrow>Active Negotiations</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
                Ongoing <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>conversations</em>
              </h2>
              {active.length === 0 ? (
                <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>No active negotiations. Go to Demo Simulation to start one.</p>
              ) : (
                active.map((neg, i) => <ActiveNegotiation key={i} neg={neg} onRefresh={reload} />)
              )}
            </section>
          )}

          {/* Demo Simulation */}
          {!loading && activeTab === 'Demo' && (
            <section>
              <Eyebrow>Demo Simulation</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 16px' }}>
                Full negotiation <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>simulation</em>
              </h2>

              {sentProposals.length === 0 ? (
                <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>No proposals available. Generate one on the Proposals page.</p>
              ) : (
                <>
                  <div style={{ marginBottom: 24 }}>
                    <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>Proposal to negotiate</label>
                    <select value={selPid} onChange={e => setSelPid(e.target.value)}
                      style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', backgroundColor: 'var(--white)', cursor: 'pointer', minWidth: 380 }}>
                      {sentProposals.map(p => (
                        <option key={p.id as string} value={p.id as string}>
                          {p.client_name as string} — {(p.opportunity_type as string).replace(/_/g, ' ')} (${(p.suggested_price as number).toLocaleString()}) [{p.status as string}]
                        </option>
                      ))}
                    </select>
                  </div>

                  <div style={{ ...card, padding: 24, marginBottom: 20 }}>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 600, color: 'var(--dark)', marginBottom: 12 }}>Step 1 — Client says: 'Price is too high'</div>
                    <button onClick={triggerTooExpensive} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', backgroundColor: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', padding: '10px 24px', cursor: 'pointer' }}>
                      Simulate 'Too Expensive' reply
                    </button>
                  </div>

                  {demoThread.length > 0 && (
                    <div style={{ ...card, padding: 24 }}>
                      <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 600, color: 'var(--dark)', marginBottom: 12 }}>Step 2 — Simulate client reply to counter-offer</div>
                      {demoThread.map((t, i) => <ThreadMessage key={i} turn={t} />)}
                      <div style={{ marginTop: 16, display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
                        <div style={{ flex: 1 }}>
                          <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>Client reply type</label>
                          <select value={simChoice} onChange={e => setSimChoice(e.target.value)}
                            style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', backgroundColor: 'var(--white)', cursor: 'pointer', width: '100%' }}>
                            {Object.keys(SIM_REPLIES).map(k => <option key={k} value={k}>{k}</option>)}
                          </select>
                          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', fontStyle: 'italic', marginTop: 6 }}>"{SIM_REPLIES[simChoice]}"</div>
                        </div>
                        <button onClick={sendSimReply} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', backgroundColor: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', padding: '10px 24px', cursor: 'pointer', flexShrink: 0 }}>
                          Send Simulated Reply
                        </button>
                      </div>
                    </div>
                  )}
                  {demoMsg && <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--status-green)', marginTop: 12 }}>{demoMsg}</div>}
                </>
              )}
            </section>
          )}

          {/* Payment Links */}
          {!loading && activeTab === 'Payments' && (
            <section>
              <Eyebrow>Stripe Payment Links</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
                Generated <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>payment links</em>
              </h2>

              {payLinks.length === 0 ? (
                <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginBottom: 24 }}>No payment links generated yet.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 32 }}>
                  {payLinks.map((link, i) => (
                    <div key={i} style={{ ...card, padding: 20 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
                        <div>
                          <div style={{ fontFamily: 'var(--fb)', fontSize: 14, fontWeight: 600, color: 'var(--dark)' }}>{link.client_name as string}</div>
                          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>
                            {(link.opportunity_type as string).replace(/_/g, ' ')} · Status: <code style={{ background: 'var(--primary-10)', color: 'var(--primary)', padding: '1px 6px', borderRadius: 4, fontSize: 11 }}>{link.status as string}</code> · {(link.created_at as string || '').slice(0, 10)}
                          </div>
                        </div>
                        <div style={{ fontFamily: 'var(--fd)', fontSize: 24, fontWeight: 300, color: 'var(--gold)' }}>${(link.suggested_price as number).toLocaleString()}</div>
                      </div>
                      <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--primary-60)', marginTop: 8, wordBreak: 'break-all' }}>
                        <a href={link.payment_link as string} target="_blank" rel="noreferrer" style={{ color: 'var(--primary-60)' }}>{link.payment_link as string}</a>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {acceptedNoLink.length > 0 && (
                <div style={{ ...card, padding: 24 }}>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 600, color: 'var(--dark)', marginBottom: 16 }}>Generate payment link manually</div>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
                    <div style={{ flex: 1 }}>
                      <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>Proposal</label>
                      <select value={payPid} onChange={e => { setPayPid(e.target.value); setPayAmount((acceptedNoLink.find(p => p.id === e.target.value)?.suggested_price as number) || 0) }}
                        style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', backgroundColor: 'var(--white)', cursor: 'pointer', width: '100%' }}>
                        {acceptedNoLink.map(p => <option key={p.id as string} value={p.id as string}>{p.client_name as string} — ${(p.suggested_price as number).toLocaleString()} [{p.status as string}]</option>)}
                      </select>
                    </div>
                    <div>
                      <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>Amount</label>
                      <input type="number" value={payAmount} min={1} onChange={e => setPayAmount(Number(e.target.value))}
                        style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', backgroundColor: 'var(--white)', width: 120 }} />
                    </div>
                    <button onClick={generateLink} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', backgroundColor: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', padding: '10px 24px', cursor: 'pointer' }}>
                      Generate Link
                    </button>
                  </div>
                  {payMsg && <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--status-green)', marginTop: 10 }}>{payMsg}</div>}
                </div>
              )}
            </section>
          )}

          {/* History */}
          {!loading && activeTab === 'History' && (
            <section>
              <Eyebrow>Negotiation History</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
                All <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>turns</em>
              </h2>
              {history.length === 0 ? (
                <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>No negotiation history yet.</p>
              ) : (
                <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', border: '1px solid var(--primary-10)' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        {['Timestamp', 'Client', 'Type', 'Turn', 'Role', 'Intent', 'Offer', 'Message'].map(h => <th key={h} style={th}>{h}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {history.slice(0, 50).map((r, i) => (
                        <tr key={i} style={{ background: i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)', borderBottom: '1px solid var(--primary-10)' }}>
                          <td style={{ ...td, color: 'var(--mid)', whiteSpace: 'nowrap' }}>{(r.timestamp as string || '').slice(0, 16).replace('T', ' ')}</td>
                          <td style={{ ...td, fontWeight: 600 }}>{r.client_name as string}</td>
                          <td style={{ ...td, color: 'var(--mid)' }}>{OPPORTUNITY_LABELS[r.opportunity_type as string] ?? (r.opportunity_type as string)}</td>
                          <td style={{ ...td, textAlign: 'center' }}>{r.turn as number}</td>
                          <td style={{ ...td, color: r.role === 'agent' ? 'var(--primary)' : 'var(--gold)' }}>{r.role as string}</td>
                          <td style={td}>{r.intent as string || '—'}</td>
                          <td style={{ ...td, color: 'var(--gold)' }}>{r.offer_price ? `$${(r.offer_price as number).toLocaleString()}` : '—'}</td>
                          <td style={{ ...td, color: 'var(--mid)', maxWidth: 300 }}>{((r.message as string) || '').slice(0, 80)}{((r.message as string) || '').length > 80 ? '…' : ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
