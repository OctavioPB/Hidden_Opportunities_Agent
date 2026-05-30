import { useState, useEffect } from 'react'
import Eyebrow from '../components/Eyebrow'
import { api, type Alert } from '../services/api'

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

function SlackCard({ alert }: { alert: Alert }) {
  const s      = alert.score
  const accent = s >= 80 ? '#e03448' : s >= 60 ? '#f07020' : '#27b97c'
  // Status badge uses spec tokens — var() works fine in style props (not SVG attrs)
  const badgeBg  = s >= 80 ? 'var(--status-red-bg)' : s >= 60 ? 'var(--status-orange-bg)' : 'var(--status-green-bg)'
  const badgeTxt = s >= 80 ? 'var(--status-red)'    : s >= 60 ? 'var(--status-orange)'    : 'var(--status-green)'
  const label    = alert.label || alert.opportunity_type || ''
  const client   = alert.client_name || 'Unknown'
  const price    = alert.suggested_price || 0
  const ts       = (alert.timestamp || '').slice(0, 16).replace('T', ' ')

  return (
    <div style={{
      borderLeft:   `4px solid ${accent}`,
      background:   'var(--primary)',          // OPB navy — replaces off-brand dark-slate
      borderRadius: 10,
      padding:      '16px 20px',
      margin:       '8px 0',
      fontFamily:   'var(--fb)',
      boxShadow:    '0 2px 6px rgba(0,0,0,0.25)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <span style={{ fontWeight: 700, color: 'rgba(255,255,255,0.85)', fontSize: 13 }}>Hidden Opportunities Agent</span>
        <span style={{ background: accent, color: '#fff', fontSize: 9, padding: '2px 8px', borderRadius: 3, fontWeight: 700, letterSpacing: '1.5px' }}>ALERT</span>
        <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: 11, marginLeft: 'auto' }}>{ts}</span>
      </div>
      <div style={{ color: 'var(--gold-light)', fontSize: 10, fontWeight: 700, marginBottom: 10, textTransform: 'uppercase', letterSpacing: '2px' }}>
        New Opportunity Detected
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 24px' }}>
        {[
          { lbl: 'Client',      val: client,                         valStyle: { color: 'rgba(255,255,255,0.85)', fontSize: 13 } },
          { lbl: 'Opportunity', val: label,                          valStyle: { color: 'rgba(255,255,255,0.85)', fontSize: 13 } },
          { lbl: 'Confidence',  val: null,                           badge: { bg: badgeBg, txt: badgeTxt, score: s } },
          { lbl: 'Price',       val: `$${price.toLocaleString()}`,   valStyle: { color: 'var(--gold-light)', fontSize: 14, fontFamily: 'var(--fd)', fontWeight: 300 } },
        ].map(({ lbl, val, valStyle, badge }) => (
          <div key={lbl}>
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 9, textTransform: 'uppercase', letterSpacing: '2px', marginBottom: 2 }}>{lbl}</div>
            {badge
              ? <span style={{ display: 'inline-block', background: badge.bg, color: badge.txt, fontSize: 12, fontWeight: 700, padding: '2px 10px', borderRadius: 12 }}>{badge.score.toFixed(0)}%</span>
              : <div style={valStyle}>{val}</div>
            }
          </div>
        ))}
      </div>
    </div>
  )
}

export default function AlertFeedPage() {
  const [alerts,     setAlerts]     = useState<Alert[]>([])
  const [loading,    setLoading]    = useState(true)
  const [running,    setRunning]    = useState(false)
  const [scope,      setScope]      = useState('All clients')
  const [minScore,   setMinScore]   = useState(60)
  const [message,    setMessage]    = useState<{ text: string; type: 'success' | 'info' } | null>(null)

  const reload = () => {
    setLoading(true)
    api.alerts.list().then(setAlerts).finally(() => setLoading(false))
  }

  useEffect(() => { reload() }, [])

  const runNow = async () => {
    setRunning(true)
    setMessage(null)
    try {
      const res = await api.alerts.run(scope, minScore)
      setMessage({ text: res.dispatched > 0 ? `Dispatched ${res.dispatched} alert(s).` : 'No opportunities above threshold.', type: res.dispatched > 0 ? 'success' : 'info' })
      reload()
    } finally {
      setRunning(false)
    }
  }

  const clearLog = async () => {
    await api.alerts.clear()
    setAlerts([])
  }

  const shown = alerts.filter(a => (a.score || 0) >= minScore)

  const selectStyle: React.CSSProperties = {
    fontFamily: 'var(--fb)', fontSize: 13, color: '#1c1c2e',
    border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)',
    padding: '8px 12px', backgroundColor: '#fff', cursor: 'pointer',
    colorScheme: 'light',
  }

  return (
    <div>
      <div style={hero}>
        <div style={wrap}>
          <Eyebrow light>Analytics</Eyebrow>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: '#fff', margin: '0 0 6px', lineHeight: 1.2 }}>
            Alert <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Feed</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'rgba(255,255,255,0.45)', margin: '0 0 32px' }}>
            Simulated Slack channel · the agent posts here every morning with newly detected opportunities
          </p>
          <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
            <div style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18 }}>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 32, fontWeight: 300, color: 'var(--gold-light)', lineHeight: 1 }}>{shown.length}</div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>Alerts Shown</div>
            </div>
            <div style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18 }}>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 32, fontWeight: 300, color: 'var(--gold-light)', lineHeight: 1 }}>{alerts.length}</div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>Total in Log</div>
            </div>
          </div>
        </div>
      </div>

      <div style={{ backgroundColor: 'var(--light)' }}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto', padding: '44px 48px', display: 'flex', flexDirection: 'column', gap: 32 }}>

          {/* Trigger panel */}
          <div style={{ ...card, padding: 28 }}>
            <Eyebrow>Trigger Detection Run</Eyebrow>
            <div style={{ display: 'flex', gap: 24, alignItems: 'flex-end', flexWrap: 'wrap', marginTop: 8 }}>
              <div>
                <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>Scope</label>
                <select style={selectStyle} value={scope} onChange={e => setScope(e.target.value)}>
                  <option>All clients</option>
                  <option>Demo clients only</option>
                </select>
              </div>
              <div>
                <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>
                  Min Confidence: {minScore}
                </label>
                <input type="range" min={0} max={100} step={5} value={minScore}
                  onChange={e => setMinScore(Number(e.target.value))}
                  style={{ width: 200, accentColor: 'var(--gold)', cursor: 'pointer' }} />
              </div>
              <button
                onClick={runNow}
                disabled={running}
                style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', backgroundColor: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', padding: '10px 24px', cursor: running ? 'wait' : 'pointer', opacity: running ? 0.7 : 1 }}>
                {running ? 'Running…' : 'Run Now'}
              </button>
              {alerts.length > 0 && (
                <button onClick={clearLog} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', background: 'none', color: 'var(--mid)', border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: '10px 20px', cursor: 'pointer' }}>
                  Clear Log
                </button>
              )}
            </div>
            {message && (
              <div style={{ marginTop: 12, fontFamily: 'var(--fb)', fontSize: 12, color: message.type === 'success' ? 'var(--status-green)' : 'var(--mid)' }}>
                {message.text}
              </div>
            )}
          </div>

          {/* Alert log */}
          <section>
            <Eyebrow>Alert Log</Eyebrow>
            <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', marginBottom: 20 }}>
              Most recent <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>dispatched alerts</em>
            </h2>

            {loading && <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>Loading alerts…</p>}

            {!loading && shown.length === 0 && (
              <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>
                No alerts yet. Click <strong>Run Now</strong> above to trigger the detection engine.
              </p>
            )}

            {!loading && shown.length > 0 && (
              <div>
                <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginBottom: 16 }}>
                  <strong style={{ color: 'var(--dark)' }}>{shown.length} alerts</strong> matching filter (of {alerts.length} total)
                </p>
                {shown.map((a, i) => <SlackCard key={i} alert={a} />)}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}
