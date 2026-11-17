import { useState, useEffect } from 'react'
import Eyebrow from '../components/Eyebrow'
import { api } from '../services/api'

const OPPORTUNITY_LABELS: Record<string, string> = {
  landing_page_optimization: 'Landing Page Optimization',
  seo_content:               'SEO Content Package',
  retargeting_campaign:      'Retargeting Campaign',
  email_automation:          'Email Automation',
  reactivation:              'Express Reactivation',
  conversion_rate_audit:     'Conversion Rate Audit',
  upsell_ad_budget:          'Ad Budget Expansion',
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
  borderRadius: 'var(--radius-md)',
  boxShadow: 'var(--shadow-card)',
  border: '1px solid var(--primary-10)',
}

type Summary = Awaited<ReturnType<typeof api.analytics.summary>>

// ── Weekly trend sparkline (hand-coded SVG) ────────────────────────────────────
function TrendChart({ data }: { data: Summary['weekly_trend'] }) {
  if (!data.length) return null
  const W = 400, H = 80
  const rates = data.map(d => d.acceptance_rate)
  const max = Math.max(...rates, 1)
  const points = data.map((d, i) => {
    const x = (i / (data.length - 1)) * (W - 20) + 10
    const y = H - 10 - ((d.acceptance_rate / max) * (H - 20))
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
      <polyline points={points.join(' ')} fill="none" stroke="#c8982a" strokeWidth={2}
                strokeLinecap="round" strokeLinejoin="round" />
      {data.map((d, i) => {
        const x = (i / (data.length - 1)) * (W - 20) + 10
        const y = H - 10 - ((d.acceptance_rate / max) * (H - 20))
        return (
          <g key={i}>
            <circle cx={x} cy={y} r={3} fill="#c8982a" />
            <text x={x} y={H - 2} textAnchor="middle" fontSize={7} fill="#9ca3af"
                  fontFamily="'Plus Jakarta Sans',sans-serif">
              {d.week_start.slice(5)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

// ── Revenue bar chart ──────────────────────────────────────────────────────────
function RevenueByType({ data }: { data: Summary['by_type'] }) {
  if (!data.length) return <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>No proposal data yet.</p>
  const max = Math.max(...data.map(d => d.revenue), 1)
  const W = 600, H = 160, PB = 28, PT = 12, PL = 8
  const bW = Math.floor((W - PL * 2) / data.length) - 8

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
      <line x1={PL} y1={H - PB} x2={W - PL} y2={H - PB} stroke="rgba(0,51,102,0.12)" strokeWidth={1} />
      {data.map((d, i) => {
        const barH = max > 0 ? Math.max(4, Math.round((d.revenue / max) * (H - PB - PT))) : 4
        const x    = PL + i * (bW + 8) + 4
        const y    = H - PB - barH
        const colors = ['#003366','#1a4d80','#336699','#4d7099','#99bbdd','#c8982a','#e8c46a']
        const col  = colors[i % colors.length]
        return (
          <g key={d.opportunity_type}>
            <rect x={x} y={y} width={bW} height={barH} fill={col} rx={3} opacity={0.85} />
            {d.revenue > 0 && (
              <text x={x + bW / 2} y={y - 3} textAnchor="middle" fill={col}
                    fontSize={8} fontFamily="'Plus Jakarta Sans',sans-serif" fontWeight="700">
                ${(d.revenue / 1000).toFixed(1)}k
              </text>
            )}
            <text x={x + bW / 2} y={H - 8} textAnchor="middle" fill="#9ca3af"
                  fontSize={7} fontFamily="'Plus Jakarta Sans',sans-serif">
              {(OPPORTUNITY_LABELS[d.opportunity_type] ?? d.opportunity_type).slice(0, 12)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

export default function AnalyticsDashboardPage() {
  const [summary,    setSummary]    = useState<Summary | null>(null)
  const [period,     setPeriod]     = useState(30)
  const [loading,    setLoading]    = useState(true)
  const [snapping,   setSnapping]   = useState(false)
  const [snapMsg,    setSnapMsg]    = useState<string | null>(null)
  const [scanning,   setScanning]   = useState(false)
  const [scanMsg,    setScanMsg]    = useState<string | null>(null)

  const reload = (p: number) => {
    setLoading(true)
    api.analytics.summary(p).then(setSummary).finally(() => setLoading(false))
  }

  useEffect(() => { reload(period) }, [period])

  const takeSnapshot = async () => {
    setSnapping(true); setSnapMsg(null)
    const res = await api.analytics.snapshot()
    setSnapMsg(`Snapshot saved for ${(res as Record<string,unknown>).snapshot_date ?? 'today'}.`)
    setSnapping(false)
  }

  const runChurnScan = async () => {
    setScanning(true); setScanMsg(null)
    const res = await api.churn.scan()
    setScanMsg(`${res.escalated} churn escalation(s) processed.`)
    setScanning(false)
  }

  const s = summary

  const th: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', padding: '11px 16px', color: '#fff', background: 'var(--primary)', textAlign: 'left' }
  const td: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 16px', color: 'var(--dark)' }
  const periods = [7, 30, 90, 0]
  const periodLabel = (p: number) => p === 0 ? 'All time' : `Last ${p} days`

  return (
    <div>
      <div style={hero}>
        <div style={wrap}>
          <Eyebrow light>Analytics</Eyebrow>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: '#fff', margin: '0 0 6px', lineHeight: 1.2 }}>
            ROI <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Dashboard</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'rgba(255,255,255,0.45)', marginBottom: 32 }}>
            Pipeline value · revenue realized · acceptance rate · time saved
          </p>
          {s && (
            <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
              {[
                { value: `$${s.pipeline_value.toLocaleString()}`,  label: 'Pipeline Detected' },
                { value: `$${s.revenue_realized.toLocaleString()}`, label: 'Revenue Realized' },
                { value: `${s.acceptance_rate}%`,                  label: 'Acceptance Rate' },
                { value: `${s.time_saved_hours}h`,                 label: 'Time Saved' },
              ].map(stat => (
                <div key={stat.label} style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18 }}>
                  <div style={{ fontFamily: 'var(--fd)', fontSize: 32, fontWeight: 300, color: 'var(--gold-light)', lineHeight: 1 }}>{stat.value}</div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>{stat.label}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={{ backgroundColor: 'var(--light)' }}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto', padding: '44px 48px', display: 'flex', flexDirection: 'column', gap: 32 }}>

          {/* Period filter + actions */}
          <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', gap: 4 }}>
              {periods.map(p => (
                <button key={p} onClick={() => setPeriod(p)} style={{
                  fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 600,
                  letterSpacing: '1px', textTransform: 'uppercase',
                  padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer',
                  background: period === p ? 'var(--primary)' : 'var(--white)',
                  color: period === p ? '#fff' : 'var(--mid)',
                  border: `1px solid ${period === p ? 'var(--primary)' : 'var(--primary-10)'}`,
                }}>
                  {periodLabel(p)}
                </button>
              ))}
            </div>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
              <button onClick={takeSnapshot} disabled={snapping} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', backgroundColor: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', padding: '8px 16px', cursor: snapping ? 'wait' : 'pointer', opacity: snapping ? 0.7 : 1 }}>
                {snapping ? 'Saving…' : 'Save Snapshot'}
              </button>
              <button onClick={runChurnScan} disabled={scanning} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', background: 'none', color: 'var(--status-red)', border: '1px solid var(--status-red-bg)', borderRadius: 'var(--radius-sm)', padding: '8px 16px', cursor: scanning ? 'wait' : 'pointer' }}>
                {scanning ? 'Scanning…' : 'Run Churn Scan'}
              </button>
            </div>
          </div>
          {snapMsg && <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--status-green)' }}>{snapMsg}</div>}
          {scanMsg && <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--status-orange)' }}>{scanMsg}</div>}

          {loading && <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>Loading analytics…</p>}

          {!loading && s && (
            <>
              {/* KPI cards row 1 */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
                {[
                  { label: 'Pipeline Detected',    value: `$${s.pipeline_value.toLocaleString()}`,   note: `${s.proposals_generated} proposals generated` },
                  { label: 'Revenue Realized',     value: `$${s.revenue_realized.toLocaleString()}`, note: `ROI: ${s.roi_pct}% of pipeline` },
                  { label: 'Acceptance Rate',      value: `${s.acceptance_rate}%`,                   note: `${s.proposals_accepted} of ${s.proposals_sent} sent` },
                  { label: 'Time Saved',           value: `${s.time_saved_hours}h`,                  note: `${s.proposals_generated} proposals × 18 min` },
                ].map(({ label, value, note }) => (
                  <div key={label} style={{ ...card, padding: 24, display: 'flex', alignItems: 'stretch', gap: 12 }}>
                    <div style={{ width: 3, backgroundColor: 'var(--gold)', borderRadius: 2, flexShrink: 0 }} />
                    <div>
                      <div style={{ fontFamily: 'var(--fd)', fontSize: 26, fontWeight: 300, color: 'var(--dark)' }}>{value}</div>
                      <div style={{ fontFamily: 'var(--fb)', fontSize: 9, textTransform: 'uppercase', letterSpacing: '2px', color: 'var(--mid)', marginTop: 4 }}>{label}</div>
                      <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginTop: 6 }}>{note}</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* KPI cards row 2 */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
                {[
                  { label: 'Clients Reached',  value: String(s.clients_reached),   color: 'var(--dark)' },
                  { label: 'Ignored',          value: String(s.proposals_ignored),  color: s.proposals_ignored > 10 ? 'var(--status-orange)' : 'var(--dark)' },
                  { label: 'Escalations',      value: String(s.escalations),        color: s.escalations > 0 ? 'var(--status-red)' : 'var(--dark)' },
                  { label: 'Follow-Ups Sent',  value: String(s.follow_ups_sent),    color: 'var(--primary-60)' },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{ ...card, padding: 20, textAlign: 'center' }}>
                    <div style={{ fontFamily: 'var(--fd)', fontSize: 32, fontWeight: 300, color }}>{value}</div>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 9, textTransform: 'uppercase', letterSpacing: '2px', color: 'var(--mid)', marginTop: 6 }}>{label}</div>
                  </div>
                ))}
              </div>

              {/* Acceptance trend + revenue by type */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                <section>
                  <Eyebrow>Weekly Trend</Eyebrow>
                  <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
                    Acceptance rate <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>over time</em>
                  </h2>
                  <div style={{ ...card, padding: 24 }}>
                    <TrendChart data={s.weekly_trend} />
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
                      {s.weekly_trend.map((w, i) => (
                        <div key={i} style={{ textAlign: 'center' }}>
                          <div style={{ fontFamily: 'var(--fd)', fontSize: 14, fontWeight: 300, color: w.acceptance_rate > 30 ? 'var(--status-green)' : 'var(--dark)' }}>{w.acceptance_rate}%</div>
                          <div style={{ fontFamily: 'var(--fb)', fontSize: 8, color: 'var(--mid)', marginTop: 2 }}>{w.sent}→{w.accepted}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>

                <section>
                  <Eyebrow>By Opportunity Type</Eyebrow>
                  <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
                    Revenue by <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>type</em>
                  </h2>
                  <div style={{ ...card, padding: 24 }}>
                    <RevenueByType data={s.by_type} />
                  </div>
                </section>
              </div>

              {/* By-type table */}
              <section>
                <Eyebrow>Breakdown</Eyebrow>
                <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
                  Performance by <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>opportunity type</em>
                </h2>
                <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', border: '1px solid var(--primary-10)' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        {['Opportunity Type', 'Proposals', 'Accepted', 'Acceptance Rate', 'Revenue'].map(h => <th key={h} style={th}>{h}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {s.by_type.map((row, i) => {
                        const rate = row.proposals > 0 ? Math.round(row.accepted / row.proposals * 100) : 0
                        return (
                          <tr key={row.opportunity_type} style={{ background: i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)', borderBottom: '1px solid var(--primary-10)' }}>
                            <td style={{ ...td, fontWeight: 600 }}>{OPPORTUNITY_LABELS[row.opportunity_type] ?? row.opportunity_type}</td>
                            <td style={{ ...td, textAlign: 'center' }}>{row.proposals}</td>
                            <td style={{ ...td, textAlign: 'center', color: row.accepted > 0 ? 'var(--status-green)' : 'var(--mid)' }}>{row.accepted}</td>
                            <td style={{ ...td, textAlign: 'center', color: rate >= 30 ? 'var(--status-green)' : rate >= 10 ? 'var(--dark)' : 'var(--mid)' }}>{rate}%</td>
                            <td style={{ ...td, textAlign: 'right', fontFamily: 'var(--fd)', fontSize: 16, fontWeight: 300, color: 'var(--gold)' }}>{row.revenue > 0 ? `$${row.revenue.toLocaleString()}` : '—'}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
