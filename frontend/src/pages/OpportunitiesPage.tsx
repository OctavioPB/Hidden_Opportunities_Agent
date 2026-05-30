import { useState, useEffect } from 'react'
import Eyebrow from '../components/Eyebrow'
import { api, type Opportunity } from '../services/api'

type UpcomingEvent = { name: string; date: string; days_away: number; types: string[]; current_boost: number }

function PropensityBadge({ tier }: { tier: string }) {
  const cfg: Record<string, { color: string; bg: string }> = {
    high:   { color: 'var(--status-green)',  bg: 'rgba(39,185,124,0.08)' },
    medium: { color: 'var(--gold)',           bg: 'rgba(200,152,42,0.08)' },
    low:    { color: 'var(--mid)',            bg: 'rgba(107,114,128,0.08)' },
  }
  const c = cfg[tier] ?? cfg.medium
  return (
    <span style={{ fontFamily: 'var(--fb)', fontSize: 8, fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase', color: c.color, background: c.bg, padding: '2px 7px', borderRadius: 'var(--radius-pill)', border: `1px solid ${c.color}30` }}>
      {tier}
    </span>
  )
}

function SeasonalBadge({ boost }: { boost: number }) {
  if (!boost || boost <= 1.0) return null
  return (
    <span style={{ fontFamily: 'var(--fb)', fontSize: 8, fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase', color: '#e8c46a', background: 'rgba(200,152,42,0.12)', padding: '2px 7px', borderRadius: 'var(--radius-pill)', border: '1px solid rgba(200,152,42,0.25)' }}>
      ↑ {((boost - 1) * 100).toFixed(0)}% seasonal
    </span>
  )
}

function SeasonalCalendarPanel({ events }: { events: UpcomingEvent[] }) {
  if (!events.length) return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {events.map(ev => (
        <div key={ev.name} style={{ display: 'flex', gap: 16, alignItems: 'center', padding: '10px 16px', background: 'rgba(200,152,42,0.05)', border: '1px solid rgba(200,152,42,0.15)', borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--gold)' }}>
          <div style={{ minWidth: 48, textAlign: 'center' }}>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, color: 'var(--gold)' }}>{ev.days_away}</div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 8, textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--mid)' }}>days</div>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 600, color: 'var(--dark)' }}>{ev.name}</div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginTop: 2 }}>{ev.date} · boosts: {ev.types.map(t => OPPORTUNITY_LABELS[t] ?? t).join(', ')}</div>
          </div>
          <span style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700, color: 'var(--gold)', background: 'rgba(200,152,42,0.1)', padding: '3px 10px', borderRadius: 'var(--radius-pill)' }}>
            ×{ev.current_boost.toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  )
}

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
  borderRadius:    'var(--radius-md)',
  boxShadow:       'var(--shadow-card)',
  border:          '1px solid var(--primary-10)',
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 80 ? 'var(--status-green)' : score >= 60 ? 'var(--status-orange)' : 'var(--primary-60)'
  const tier  = score >= 80 ? 'HIGH' : score >= 60 ? 'MEDIUM' : 'LOW'
  const bg    = score >= 80 ? 'rgba(39,185,124,0.08)' : score >= 60 ? 'rgba(240,112,32,0.08)' : 'rgba(51,102,153,0.08)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '8px 0' }}>
      <div style={{ flex: 1, background: 'var(--primary-10)', borderRadius: 4, height: 7, overflow: 'hidden' }}>
        <div style={{ width: `${score}%`, background: color, height: '100%', borderRadius: 4, transition: 'width 0.4s' }} />
      </div>
      <span style={{
        fontFamily:    'var(--fb)',
        fontSize:      10,
        fontWeight:    700,
        letterSpacing: '0.8px',
        textTransform: 'uppercase',
        background:    bg,
        color,
        padding:       '3px 11px',
        borderRadius:  'var(--radius-pill)',
        minWidth:      120,
        textAlign:     'center',
        border:        `1px solid ${color}30`,
      }}>
        {tier} &nbsp;{score.toFixed(0)}/100
      </span>
    </div>
  )
}

export default function OpportunitiesPage() {
  const [data,        setData]        = useState<Opportunity[]>([])
  const [meta,        setMeta]        = useState<{ types: string[]; industries: string[] }>({ types: [], industries: [] })
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState<string | null>(null)
  const [selType,     setSelType]     = useState('All')
  const [selIndustry, setSelIndustry] = useState('All')
  const [demoOnly,    setDemoOnly]    = useState(false)
  const [selPropensity, setSelPropensity] = useState('All')
  const [events,      setEvents]      = useState<UpcomingEvent[]>([])
  const [showCalendar, setShowCalendar] = useState(false)
  const [view,        setView]        = useState<'Cards' | 'Table'>('Cards')

  useEffect(() => {
    api.opportunities.meta().then(setMeta).catch(() => null)
    api.seasonal.upcoming(8).then(setEvents).catch(() => null)
  }, [])

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.opportunities.list(selType, selIndustry, demoOnly)
      .then(d => {
        const filtered = selPropensity !== 'All' ? d.filter((r: Opportunity) => (r as unknown as Record<string, unknown>).propensity_tier === selPropensity) : d
        setData(filtered)
      })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [selType, selIndustry, demoOnly, selPropensity])

  const totalClients = new Set(data.map(r => r.client_id)).size
  const highConf     = data.filter(r => r.score >= 80).length
  const totalValue   = data.reduce((s, r) => s + r.suggested_price, 0)

  const selectStyle: React.CSSProperties = {
    fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)',
    border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)',
    padding: '8px 12px', backgroundColor: 'var(--white)', cursor: 'pointer',
  }

  const tabBtn = (active: boolean): React.CSSProperties => ({
    background: 'none', border: 'none', cursor: 'pointer',
    fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 500,
    letterSpacing: '1.5px', textTransform: 'uppercase',
    padding: '8px 20px', marginBottom: -1,
    borderBottom: `2px solid ${active ? 'var(--gold)' : 'transparent'}`,
    color: active ? 'var(--gold)' : 'var(--mid)',
    transition: 'color 0.15s',
  })

  return (
    <div>
      {/* ── Hero ── */}
      <div style={hero}>
        <div style={wrap}>
          <Eyebrow light>Intelligence</Eyebrow>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: '#fff', margin: '0 0 6px', lineHeight: 1.2 }}>
            Detected <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Opportunities</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'rgba(255,255,255,0.45)', margin: '0 0 32px' }}>
            All clients scanned daily · opportunities ranked by confidence score · 0–100
          </p>
          <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
            {[
              { value: String(totalClients),          label: 'Clients with Opportunities' },
              { value: String(data.length),           label: 'Total Opportunities' },
              { value: String(highConf),              label: 'High Confidence (>80)' },
              { value: `$${totalValue.toLocaleString()}`, label: 'Pipeline Value' },
            ].map(s => (
              <div key={s.label} style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18, minWidth: 120 }}>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 32, fontWeight: 300, color: 'var(--gold-light)', lineHeight: 1 }}>{s.value}</div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Body ── */}
      <div style={{ backgroundColor: 'var(--light)' }}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto', padding: '44px 48px', display: 'flex', flexDirection: 'column', gap: 32 }}>

          {/* Filters */}
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div>
              <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>Opportunity Type</label>
              <select style={selectStyle} value={selType} onChange={e => setSelType(e.target.value)}>
                <option value="All">All Types</option>
                {meta.types.map(t => <option key={t} value={t}>{OPPORTUNITY_LABELS[t] ?? t}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>Industry</label>
              <select style={selectStyle} value={selIndustry} onChange={e => setSelIndustry(e.target.value)}>
                <option value="All">All Industries</option>
                {meta.industries.map(i => <option key={i} value={i}>{i}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>Propensity</label>
              <select style={selectStyle} value={selPropensity} onChange={e => setSelPropensity(e.target.value)}>
                <option value="All">All Tiers</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', cursor: 'pointer', paddingBottom: 2 }}>
              <input type="checkbox" checked={demoOnly} onChange={e => setDemoOnly(e.target.checked)} />
              Demo clients only
            </label>
            <button onClick={() => setShowCalendar(c => !c)} style={{ marginLeft: 'auto', fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', background: showCalendar ? 'var(--gold)' : 'none', color: showCalendar ? '#fff' : 'var(--gold)', border: '1px solid var(--gold)', borderRadius: 'var(--radius-sm)', padding: '8px 14px', cursor: 'pointer', paddingBottom: 8 }}>
              {showCalendar ? '▾' : '▸'} Seasonal Calendar
            </button>
          </div>

          {/* Seasonal calendar panel */}
          {showCalendar && (
            <div style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', padding: 24, border: '1px solid var(--primary-10)', boxShadow: 'var(--shadow-card)' }}>
              <Eyebrow>Upcoming Events</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 16px' }}>
                Seasonal <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>opportunity boosts</em>
              </h2>
              {events.length === 0 ? (
                <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>No seasonal events in the next 8 weeks.</p>
              ) : (
                <SeasonalCalendarPanel events={events} />
              )}
            </div>
          )}

          {/* View toggle */}
          <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--primary-10)' }}>
            <button style={tabBtn(view === 'Cards')} onClick={() => setView('Cards')}>Cards</button>
            <button style={tabBtn(view === 'Table')} onClick={() => setView('Table')}>Table</button>
          </div>

          {loading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', padding: '40px 0' }}>
              <div style={{ width: 16, height: 16, borderRadius: '50%', border: '2px solid var(--primary-10)', borderTopColor: 'var(--gold)', animation: 'spin 0.8s linear infinite' }} />
              Loading opportunities…
            </div>
          )}

          {error && (
            <div style={{ textAlign: 'center', padding: '60px 0' }}>
              <p style={{ fontFamily: 'var(--fd)', fontSize: 18, color: 'var(--status-orange)', marginBottom: 6 }}>Could not load data.</p>
              <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>{error} — ensure the backend is running.</p>
            </div>
          )}

          {!loading && !error && data.length === 0 && (
            <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>No opportunities detected. Run the daily job to refresh.</p>
          )}

          {!loading && !error && data.length > 0 && view === 'Cards' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {data.map((r, i) => (
                <div key={i} style={{ ...card, padding: 28 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                    <div>
                      <div style={{ fontFamily: 'var(--fb)', fontSize: 14, fontWeight: 600, color: 'var(--dark)' }}>
                        {r.client_name}{r.is_demo_scenario ? ' [Demo]' : ''} &nbsp;·&nbsp;
                        <span style={{ fontWeight: 400, fontStyle: 'italic', color: 'var(--mid)' }}>{r.industry}</span>
                      </div>
                      <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 600, color: 'var(--primary)', marginTop: 2 }}>
                        {OPPORTUNITY_LABELS[r.opportunity_type] ?? r.label}
                      </div>
                      <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                        <PropensityBadge tier={(r as unknown as Record<string, unknown>).propensity_tier as string ?? 'medium'} />
                        <SeasonalBadge boost={(r as unknown as Record<string, unknown>).seasonal_boost as number ?? 1} />
                      </div>
                    </div>
                    <div style={{ fontFamily: 'var(--fd)', fontSize: 24, fontWeight: 300, color: 'var(--gold)', flexShrink: 0 }}>
                      ${r.suggested_price.toLocaleString()}
                    </div>
                  </div>
                  <ScoreBar score={r.score} />
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginTop: 6 }}>
                    Signals: {r.triggered_signals.map(s => (
                      <code key={s} style={{ background: 'var(--primary-10)', color: 'var(--primary)', padding: '1px 6px', borderRadius: 4, fontSize: 10, marginRight: 4 }}>{s.replace(/_/g, ' ')}</code>
                    ))}
                  </div>
                  <blockquote style={{ borderLeft: '2px solid var(--gold)', background: 'rgba(200,152,42,0.04)', padding: '8px 14px', borderRadius: '0 6px 6px 0', margin: '10px 0 0', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', fontStyle: 'italic' }}>
                    {r.rationale}
                  </blockquote>
                </div>
              ))}
            </div>
          )}

          {!loading && !error && data.length > 0 && view === 'Table' && (
            <OppTable rows={data} />
          )}
        </div>
      </div>
    </div>
  )
}

function OppTable({ rows }: { rows: Opportunity[] }) {
  const [sortKey, setSortKey] = useState<string>('score')
  const [asc,     setAsc]     = useState(false)

  const sorted = [...rows].sort((a, b) => {
    const av = (a as unknown as Record<string, unknown>)[sortKey]
    const bv = (b as unknown as Record<string, unknown>)[sortKey]
    const cmp = (av as number) < (bv as number) ? -1 : (av as number) > (bv as number) ? 1 : 0
    return asc ? cmp : -cmp
  })

  const toggle = (k: string) => { if (sortKey === k) setAsc(a => !a); else { setSortKey(k); setAsc(false) } }
  const arrow  = (k: string) => sortKey === k ? (asc ? ' ▴' : ' ▾') : ''

  const th: React.CSSProperties = {
    fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '2px',
    textTransform: 'uppercase', padding: '11px 14px', color: '#fff',
    background: 'var(--primary)', whiteSpace: 'nowrap', cursor: 'pointer',
    textAlign: 'left',
  }
  const td: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 14px', color: 'var(--dark)' }

  return (
    <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', border: '1px solid var(--primary-10)' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={th} onClick={() => toggle('client_name')}>Client{arrow('client_name')}</th>
            <th style={th}>Industry</th>
            <th style={th}>Opportunity</th>
            <th style={th} onClick={() => toggle('score')}>Score{arrow('score')}</th>
            <th style={th} onClick={() => toggle('suggested_price')}>Price{arrow('suggested_price')}</th>
            <th style={th}>Demo</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, i) => (
            <tr key={i} style={{ background: i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)', borderBottom: '1px solid var(--primary-10)' }}>
              <td style={{ ...td, fontWeight: 600 }}>{r.client_name}</td>
              <td style={{ ...td, color: 'var(--mid)' }}>{r.industry}</td>
              <td style={td}>{OPPORTUNITY_LABELS[r.opportunity_type] ?? r.label}</td>
              <td style={td}>
                <span style={{ fontFamily: 'var(--fd)', fontSize: 15, fontWeight: 300, color: r.score >= 80 ? 'var(--status-green)' : r.score >= 60 ? 'var(--status-orange)' : 'var(--dark)' }}>
                  {r.score.toFixed(0)}
                </span>
              </td>
              <td style={{ ...td, color: 'var(--gold)', fontWeight: 600 }}>${r.suggested_price.toLocaleString()}</td>
              <td style={td}>{r.is_demo_scenario ? '✓' : ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
