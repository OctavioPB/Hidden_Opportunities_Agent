import { useState, useEffect } from 'react'
import Eyebrow from '../components/Eyebrow'
import { api, type TextSummary, type SignalEntry, type Client } from '../services/api'

const SIGNAL_LABELS: Record<string, string> = {
  mentions_price:   'Price Concern',
  asks_for_results: 'Asks for Results',
  churn_risk:       'Churn Risk',
  urgency_signal:   'Urgency',
  interest_signal:  'Interest Signal',
}
const SIGNAL_COLORS: Record<string, string> = {
  mentions_price:   '#c8982a',
  asks_for_results: '#336699',
  churn_risk:       '#e03448',
  urgency_signal:   '#f07020',
  interest_signal:  '#27b97c',
}
// Explicit rgba badge backgrounds — no hex-opacity shorthand (${color}1A is non-standard)
const SIGNAL_BG: Record<string, string> = {
  mentions_price:   'rgba(200,152,42,0.10)',
  asks_for_results: 'rgba(51,102,153,0.10)',
  churn_risk:       'var(--status-red-bg)',
  urgency_signal:   'var(--status-orange-bg)',
  interest_signal:  'var(--status-green-bg)',
}
const SIGNAL_BORDER: Record<string, string> = {
  mentions_price:   'rgba(200,152,42,0.30)',
  asks_for_results: 'rgba(51,102,153,0.30)',
  churn_risk:       'rgba(224,52,72,0.30)',
  urgency_signal:   'rgba(240,112,32,0.30)',
  interest_signal:  'rgba(39,185,124,0.30)',
}
const SOURCE_LABELS: Record<string, string> = {
  email:           'Email',
  call_transcript: 'Call',
  crm_note:        'CRM',
}

const hero: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  backgroundImage: `linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)`,
  backgroundSize: '48px 48px',
  padding: '56px 48px',
}
const wrap: React.CSSProperties = { maxWidth: 'var(--max-width-dashboard)', margin: '0 auto' }
const card: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  borderRadius:    'var(--radius-md)',
  boxShadow:       'var(--shadow-card)',
  border:          '1px solid var(--primary-10)',
}

function SignalBadge({ label, color, bg, border }: { label: string; color: string; bg: string; border: string }) {
  return (
    <span style={{ background: bg, color, fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '1px', textTransform: 'uppercase', padding: '3px 9px', borderRadius: 'var(--radius-pill)', margin: 2, border: `1px solid ${border}`, display: 'inline-block' }}>
      {label}
    </span>
  )
}

function sentimentColor(s: number | null) {
  if (s == null) return '#6b7280'
  if (s > 0.2) return '#27b97c'
  if (s < -0.2) return '#e03448'
  return '#c8982a'
}

// Maps a palette hex to its rgba badge-bg and badge-border — keeps SignalBadge spec-compliant
const COLOR_BG: Record<string, string> = {
  '#27b97c': 'var(--status-green-bg)',
  '#e03448': 'var(--status-red-bg)',
  '#f07020': 'var(--status-orange-bg)',
  '#c8982a': 'rgba(200,152,42,0.10)',
  '#6b7280': 'rgba(107,114,128,0.10)',
}
const COLOR_BORDER: Record<string, string> = {
  '#27b97c': 'rgba(39,185,124,0.30)',
  '#e03448': 'rgba(224,52,72,0.30)',
  '#f07020': 'rgba(240,112,32,0.30)',
  '#c8982a': 'rgba(200,152,42,0.30)',
  '#6b7280': 'rgba(107,114,128,0.30)',
}

// Hand-coded SVG bar chart for signal distribution
function SignalDistributionChart({ counts }: { counts: Record<string, number> }) {
  const data = [
    { label: 'Price Concern',    value: counts.price_mentions   ?? 0, color: '#c8982a' },
    { label: 'Asks Results',     value: counts.results_queries  ?? 0, color: '#336699' },
    { label: 'Churn Risk',       value: counts.churn_flags      ?? 0, color: '#e03448' },
    { label: 'Urgency',          value: counts.urgency_flags    ?? 0, color: '#f07020' },
    { label: 'Interest',         value: counts.interest_flags   ?? 0, color: '#27b97c' },
  ]
  const maxVal = Math.max(...data.map(d => d.value), 1)
  const W = 500, H = 180, PB = 36, PT = 12, PL = 8, PR = 8
  const bW = Math.floor((W - PL - PR) / data.length) - 8

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
      <line x1={PL} y1={H - PB} x2={W - PR} y2={H - PB} stroke="rgba(0,51,102,0.12)" strokeWidth={1} />
      {data.map((d, i) => {
        const barH = (d.value / maxVal) * (H - PB - PT)
        const x    = PL + i * (bW + 8) + 4
        const y    = PT + (H - PB - PT) - barH
        return (
          <g key={d.label}>
            <rect x={x} y={y} width={bW} height={barH} fill={d.color} rx={4} opacity={0.83} />
            {d.value > 0 && (
              <text x={x + bW / 2} y={y - 4} textAnchor="middle" fill="#1c1c2e" fontSize={10} fontFamily="'Plus Jakarta Sans',sans-serif">{d.value}</text>
            )}
            <text x={x + bW / 2} y={H - 8} textAnchor="middle" fill="#9ca3af" fontSize={8} fontFamily="'Plus Jakarta Sans',sans-serif">{d.label}</text>
          </g>
        )
      })}
    </svg>
  )
}

export default function TextSignalsPage() {
  const [summary,     setSummary]     = useState<TextSummary | null>(null)
  const [clients,     setClients]     = useState<Client[]>([])
  const [allSummaries,setAllSummaries]= useState<Record<string, unknown>[]>([])
  const [urgency,     setUrgency]     = useState<Record<string, unknown>[]>([])
  const [selClient,   setSelClient]   = useState<string>('')
  const [clientData,  setClientData]  = useState<{ signals: SignalEntry[]; summary: Record<string, unknown> } | null>(null)
  const [loading,     setLoading]     = useState(true)
  const [processing,  setProcessing]  = useState(false)
  const [processMsg,  setProcessMsg]  = useState<string | null>(null)
  const [activeTab,   setActiveTab]   = useState<'Browser' | 'Matrix' | 'Urgency' | 'Churn'>('Browser')
  const [churnLog,    setChurnLog]    = useState<Record<string, unknown>[]>([])
  const [scanning,    setScanning]    = useState(false)
  const [scanMsg,     setScanMsg]     = useState<string | null>(null)

  const reload = () => {
    setLoading(true)
    Promise.all([
      api.textSignals.summary(),
      api.clients.list(),
      api.textSignals.allSummaries(),
      api.textSignals.urgency(),
    ]).then(([s, c, as_, u]) => {
      setSummary(s)
      setClients(c)
      setAllSummaries(as_)
      setUrgency(u)
      if (c.length > 0 && !selClient) setSelClient(c[0].id)
    }).finally(() => setLoading(false))
  }

  useEffect(() => { reload() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!selClient) return
    api.textSignals.client(selClient).then(setClientData)
  }, [selClient])

  const process = async (reprocess_all = false) => {
    setProcessing(true); setProcessMsg(null)
    const res = await api.textSignals.process(reprocess_all)
    setProcessMsg(`Done! Processed ${res.total_processed} texts · Churn alerts: ${res.churn_alerts} · Urgency alerts: ${res.urgency_alerts}`)
    reload()
    setProcessing(false)
  }

  const runChurnScan = async () => {
    setScanning(true); setScanMsg(null)
    const res = await api.churn.scan()
    setScanMsg(`${res.escalated} churn escalation(s) processed.`)
    api.churn.log().then(setChurnLog)
    setScanning(false)
  }

  useEffect(() => {
    if (activeTab === 'Churn') api.churn.log().then(setChurnLog)
  }, [activeTab])

  const tabBtn = (t: string): React.CSSProperties => ({
    background: 'none', border: 'none', cursor: 'pointer',
    fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 500,
    letterSpacing: '1.5px', textTransform: 'uppercase',
    padding: '8px 20px', marginBottom: -1,
    borderBottom: `2px solid ${activeTab === t ? 'var(--gold)' : 'transparent'}`,
    color: activeTab === t ? 'var(--gold)' : 'var(--mid)', transition: 'color 0.15s',
  })

  const th: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', padding: '11px 14px', color: '#fff', background: 'var(--primary)', textAlign: 'left' }
  const td: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 14px', color: 'var(--dark)' }

  const unproc = summary?.unprocessed ?? 0

  return (
    <div>
      <div style={hero}>
        <div style={wrap}>
          <Eyebrow light>Intelligence</Eyebrow>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: '#fff', margin: '0 0 6px', lineHeight: 1.2 }}>
            Text Signals — <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Active Listener</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'rgba(255,255,255,0.45)', margin: '0 0 32px' }}>
            Reads emails, call transcripts, and CRM notes · extracts signals · improves ML accuracy
          </p>
          {summary && (
            <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
              {[
                { value: String(summary.total_signals), label: 'Total Texts' },
                { value: String(summary.processed),     label: 'Processed' },
                { value: String(summary.churn_count),   label: 'Churn Flags' },
                { value: String(summary.urgency_count), label: 'Urgency Flags' },
              ].map(s => (
                <div key={s.label} style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18 }}>
                  <div style={{ fontFamily: 'var(--fd)', fontSize: 32, fontWeight: 300, color: 'var(--gold-light)', lineHeight: 1 }}>{s.value}</div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>{s.label}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={{ backgroundColor: 'var(--light)' }}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto', padding: '44px 48px', display: 'flex', flexDirection: 'column', gap: 32 }}>

          {/* Process panel */}
          <div style={{ ...card, padding: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
            <div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)' }}>
                {unproc > 0 ? `${unproc} of ${summary?.total_signals ?? 0} texts still need signal extraction.` : `All ${summary?.total_signals ?? 0} texts are processed.`}
              </div>
              {processMsg && <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--status-green)', marginTop: 6 }}>{processMsg}</div>}
            </div>
            <button onClick={() => process(unproc === 0)} disabled={processing} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', backgroundColor: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', padding: '10px 24px', cursor: processing ? 'wait' : 'pointer', opacity: processing ? 0.7 : 1, flexShrink: 0 }}>
              {processing ? 'Processing…' : 'Process Emails Now'}
            </button>
          </div>

          {/* Signal distribution */}
          {summary && (
            <section>
              <Eyebrow>Signal Overview</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
                Signal type <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>distribution</em>
              </h2>
              <div style={{ ...card, padding: 28 }}>
                <SignalDistributionChart counts={summary.counts_by_type} />
              </div>
            </section>
          )}

          {/* Tab toggle */}
          <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--primary-10)' }}>
            <button style={tabBtn('Browser')} onClick={() => setActiveTab('Browser')}>Email Browser</button>
            <button style={tabBtn('Matrix')}  onClick={() => setActiveTab('Matrix')}>Signal Matrix</button>
            <button style={tabBtn('Urgency')} onClick={() => setActiveTab('Urgency')}>Urgency Alerts</button>
            <button style={tabBtn('Churn')}   onClick={() => setActiveTab('Churn')}>Churn Escalations</button>
          </div>

          {loading && <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>Loading…</p>}

          {/* Email Browser */}
          {!loading && activeTab === 'Browser' && (
            <section>
              <Eyebrow>Email Browser</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 16px' }}>
                Client <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>communications</em>
              </h2>
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>Client</label>
                <select value={selClient} onChange={e => setSelClient(e.target.value)}
                  style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#1c1c2e', border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', backgroundColor: '#fff', cursor: 'pointer', colorScheme: 'light' }}>
                  {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>

              {clientData && (
                <div>
                  {clientData.signals.length === 0 && (
                    <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>No communications found. Process emails first.</p>
                  )}
                  {clientData.signals.map((sig, i) => {
                    const source = SOURCE_LABELS[sig.source] ?? sig.source
                    const sent   = sig.sentiment
                    const sc     = sentimentColor(sent)
                    return (
                      <div key={i} style={{ ...card, padding: '12px 16px', marginBottom: 8 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                          <span style={{ fontFamily: 'var(--fb)', fontSize: 9, textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 500, color: 'var(--mid)' }}>{source}</span>
                          {sent != null && <SignalBadge label={`Sentiment: ${sent.toFixed(2)}`} color={sc} bg={COLOR_BG[sc] ?? 'rgba(107,114,128,0.10)'} border={COLOR_BORDER[sc] ?? 'rgba(107,114,128,0.30)'} />}
                          {Object.keys(SIGNAL_LABELS).filter(k => (sig as unknown as Record<string, unknown>)[k]).map(k => (
                            <SignalBadge key={k} label={SIGNAL_LABELS[k]} color={SIGNAL_COLORS[k]} bg={SIGNAL_BG[k]} border={SIGNAL_BORDER[k]} />
                          ))}
                          <span style={{ marginLeft: 'auto', fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--primary-30)' }}>
                            {(sig.processed_at || '').slice(0, 16).replace('T', ' ')}
                          </span>
                        </div>
                        <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', fontStyle: 'italic', borderLeft: '2px solid var(--primary-10)', paddingLeft: 10 }}>
                          "{sig.raw_text}"
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </section>
          )}

          {/* Signal Matrix */}
          {!loading && activeTab === 'Matrix' && (
            <section>
              <Eyebrow>Signal Matrix</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 8px' }}>
                All clients — <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>signal overview</em>
              </h2>
              <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginBottom: 20 }}>Sorted by Churn Risk. Darker = signal active.</p>
              {allSummaries.length === 0 ? (
                <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>No signal summaries found. Process emails first.</p>
              ) : (
                <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', border: '1px solid var(--primary-10)' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        {['Client', 'Sentiment', '💰 Price', '📊 Results', '🚨 Churn', '⚡ Urgency', '✅ Interest', '# Signals'].map(h => <th key={h} style={th}>{h}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {([...allSummaries] as Record<string, unknown>[]).sort((a, b) => (b.churn_risk as number) - (a.churn_risk as number)).map((s, i) => {
                        const clientId = s.client_id as string
                        const clientName = clients.find(c => c.id === clientId)?.name ?? clientId
                        const bool = (v: unknown) => v ? '✓' : ''
                        const sentVal = s.sentiment_score as number | null
                        return (
                          <tr key={i} style={{ background: i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)', borderBottom: '1px solid var(--primary-10)' }}>
                            <td style={{ ...td, fontWeight: 600 }}>{clientName}</td>
                            <td style={{ ...td, color: sentimentColor(sentVal) }}>{sentVal != null ? sentVal.toFixed(2) : '—'}</td>
                            <td style={{ ...td, textAlign: 'center', color: s.mentions_price ? '#c8982a' : 'var(--mid)' }}>{bool(s.mentions_price)}</td>
                            <td style={{ ...td, textAlign: 'center', color: s.asks_for_results ? '#336699' : 'var(--mid)' }}>{bool(s.asks_for_results)}</td>
                            <td style={{ ...td, textAlign: 'center', color: s.churn_risk ? 'var(--status-red)' : 'var(--mid)', fontWeight: s.churn_risk ? 700 : 400 }}>{bool(s.churn_risk)}</td>
                            <td style={{ ...td, textAlign: 'center', color: s.urgency_signal ? 'var(--status-orange)' : 'var(--mid)' }}>{bool(s.urgency_signal)}</td>
                            <td style={{ ...td, textAlign: 'center', color: s.interest_signal ? 'var(--status-green)' : 'var(--mid)' }}>{bool(s.interest_signal)}</td>
                            <td style={{ ...td, textAlign: 'center' }}>{s.n_signals as number ?? 0}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          )}

          {/* Urgency Alerts */}
          {!loading && activeTab === 'Urgency' && (
            <section>
              <Eyebrow>Urgency Alerts</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 16px' }}>
                Clients requiring <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>immediate attention</em>
              </h2>
              {urgency.length === 0 ? (
                <div style={{ ...card, padding: 24, color: 'var(--status-green)', fontFamily: 'var(--fb)', fontSize: 13 }}>
                  No urgency or churn alerts detected. All clients look healthy.
                </div>
              ) : urgency.map((a, i) => {
                const churn      = !!a.churn_risk
                const urgent     = !!a.urgency_signal
                const accentColor = churn ? '#e03448' : '#f07020'
                const icon    = churn ? '🚨' : '⚡'
                const label   = churn ? 'CHURN RISK' : 'URGENCY'
                const sentVal = a.avg_sentiment as number | null
                const texts   = ((a.combined_text as string) || '').split(' ||| ')
                const snippet = texts[0] ? (texts[0].length > 120 ? texts[0].slice(0, 120) + '…' : texts[0]) : ''
                return (
                  <div key={i} style={{ backgroundColor: 'var(--white)', borderLeft: `4px solid ${accentColor}`, borderRadius: 8, border: '1px solid var(--primary-10)', padding: '14px 20px', margin: '8px 0', boxShadow: 'var(--shadow-card)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                      <span style={{ fontSize: '1.3em' }}>{icon}</span>
                      <span style={{ fontFamily: 'var(--fb)', fontWeight: 600, fontSize: '0.95em', color: 'var(--dark)' }}>{a.client_name as string}</span>
                      <span style={{ fontFamily: 'var(--fb)', fontSize: '0.82em', color: 'var(--mid)' }}>· {a.industry as string}</span>
                      <span style={{ marginLeft: 'auto' }}>
                        <SignalBadge label={label} color={accentColor} bg={COLOR_BG[accentColor] ?? 'rgba(224,52,72,0.08)'} border={COLOR_BORDER[accentColor] ?? 'rgba(224,52,72,0.30)'} />
                        {churn && urgent && <SignalBadge label="⚡ URGENCY" color="#f07020" bg="var(--status-orange-bg)" border="rgba(240,112,32,0.30)" />}
                      </span>
                    </div>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: '0.8em', color: 'var(--mid)', marginBottom: 6 }}>
                      Account manager: <strong style={{ color: 'var(--primary)' }}>{a.account_manager as string || '—'}</strong>
                      &nbsp;·&nbsp; Sentiment: {sentVal != null ? sentVal.toFixed(2) : 'pending'}
                    </div>
                    {snippet && (
                      <div style={{ fontFamily: 'var(--fb)', fontSize: '0.85em', color: 'var(--mid)', fontStyle: 'italic', borderLeft: '2px solid var(--primary-10)', paddingLeft: 10 }}>
                        "{snippet}"
                      </div>
                    )}
                  </div>
                )
              })}
            </section>
          )}
          {/* Churn Escalations (Feature 3) */}
          {!loading && activeTab === 'Churn' && (
            <section>
              <Eyebrow>Churn Prevention</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 16px' }}>
                Escalation <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>log</em>
              </h2>
              <div style={{ display: 'flex', gap: 16, marginBottom: 20, alignItems: 'center' }}>
                <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', flex: 1 }}>
                  Clients with active churn or urgency signals. The agent automatically notifies their account manager.
                </p>
                <button onClick={runChurnScan} disabled={scanning} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', backgroundColor: 'var(--status-red)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', padding: '10px 20px', cursor: scanning ? 'wait' : 'pointer', opacity: scanning ? 0.7 : 1, flexShrink: 0 }}>
                  {scanning ? 'Scanning…' : 'Run Churn Scan Now'}
                </button>
              </div>
              {scanMsg && <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--status-green)', marginBottom: 16 }}>{scanMsg}</div>}

              {churnLog.length === 0 ? (
                <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>
                  No escalations recorded yet. Run the churn scan or process NLP emails first.
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {churnLog.map((entry, i) => {
                    const churnSignal = entry.churn_signal as string ?? ''
                    const color = churnSignal === 'churn_risk' ? 'var(--status-red)' : 'var(--status-orange)'
                    const bg    = churnSignal === 'churn_risk' ? 'rgba(224,52,72,0.06)' : 'rgba(240,112,32,0.06)'
                    return (
                      <div key={i} style={{ backgroundColor: 'var(--white)', borderLeft: `3px solid ${color}`, border: '1px solid var(--primary-10)', borderRadius: 8, padding: '14px 20px', boxShadow: 'var(--shadow-card)' }}>
                        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 8 }}>
                          <span style={{ fontFamily: 'var(--fb)', fontSize: 14, fontWeight: 700, color: 'var(--dark)' }}>{entry.client_name as string ?? entry.client_id as string}</span>
                          <span style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px', color, background: bg, padding: '2px 8px', borderRadius: 'var(--radius-pill)' }}>
                            {churnSignal.replace('_', ' ')}
                          </span>
                          <span style={{ marginLeft: 'auto', fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>
                            {(entry.escalated_at as string ?? '').slice(0, 10)}
                          </span>
                        </div>
                        <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>
                          Account manager: <strong style={{ color: 'var(--primary)' }}>{entry.account_manager as string ?? '—'}</strong>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
