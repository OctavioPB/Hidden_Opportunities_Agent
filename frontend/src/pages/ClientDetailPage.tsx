import { useState, useEffect } from 'react'
import Eyebrow from '../components/Eyebrow'
import { api, type ClientDetail } from '../services/api'

const OPPORTUNITY_LABELS: Record<string, string> = {
  landing_page_optimization: 'Landing Page Optimization',
  seo_content:               'SEO Content Package',
  retargeting_campaign:      'Retargeting Campaign',
  email_automation:          'Email Automation',
  reactivation:              'Express Reactivation',
  conversion_rate_audit:     'Conversion Rate Audit',
  upsell_ad_budget:          'Ad Budget Expansion',
}

const STATUS_DOT: Record<string, string> = {
  draft:    '#f07020', approved: '#27b97c', sent: '#003366',
  accepted: '#27b97c', rejected: '#e03448', paid: '#7c4dbd',
}

const hero: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  backgroundImage: `linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)`,
  backgroundSize: '48px 48px',
  padding: '44px 48px 40px',
}
const wrap: React.CSSProperties  = { maxWidth: 'var(--max-width-dashboard)', margin: '0 auto' }
const body: React.CSSProperties  = { maxWidth: 'var(--max-width-dashboard)', margin: '0 auto', padding: '40px 48px', display: 'flex', flexDirection: 'column', gap: 36 }
const card: React.CSSProperties  = { backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', border: '1px solid var(--primary-10)' }

function fmt(n: number | undefined | null, decimals = 1): string {
  if (n == null) return '—'
  return Number(n).toFixed(decimals)
}
function pct(n: number | undefined | null): string {
  if (n == null) return '—'
  return (Number(n) * 100).toFixed(1) + '%'
}

function KpiCard({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div style={{ ...card, padding: '18px 20px' }}>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 8 }}>{label}</div>
      <div style={{ fontFamily: 'var(--fd)', fontSize: 26, fontWeight: 300, color: 'var(--dark)', lineHeight: 1 }}>{value}</div>
      {note && <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)', marginTop: 4 }}>{note}</div>}
    </div>
  )
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 80 ? 'var(--status-green)' : score >= 60 ? 'var(--gold)' : 'var(--status-orange)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{ flex: 1, height: 6, background: 'var(--primary-10)', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${score}%`, height: '100%', background: color, borderRadius: 3 }} />
      </div>
      <span style={{ fontFamily: 'var(--fd)', fontSize: 15, fontWeight: 300, color, minWidth: 30, textAlign: 'right' }}>{score.toFixed(0)}</span>
    </div>
  )
}

function SignalFlag({ label, active, color }: { label: string; active: boolean; color: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', background: active ? `${color}12` : 'rgba(107,114,128,0.05)', border: `1px solid ${active ? color + '30' : 'var(--primary-10)'}`, borderRadius: 'var(--radius-sm)', opacity: active ? 1 : 0.5 }}>
      <div style={{ width: 7, height: 7, borderRadius: '50%', background: active ? color : 'var(--mid)', flexShrink: 0 }} />
      <span style={{ fontFamily: 'var(--fb)', fontSize: 11, fontWeight: active ? 600 : 400, color: active ? 'var(--dark)' : 'var(--mid)' }}>{label}</span>
    </div>
  )
}

export default function ClientDetailPage({ clientId, onBack }: { clientId: string; onBack: () => void }) {
  const [data,    setData]    = useState<ClientDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.clients.detail(clientId)
      .then(setData)
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [clientId])

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: 12, fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>
      <div style={{ width: 18, height: 18, border: '2px solid var(--primary-10)', borderTopColor: 'var(--gold)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
      Loading client data…
    </div>
  )

  if (error || !data) return (
    <div style={{ textAlign: 'center', padding: '80px 48px' }}>
      <p style={{ fontFamily: 'var(--fd)', fontSize: 18, color: 'var(--status-orange)', marginBottom: 6 }}>Could not load client.</p>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginBottom: 24 }}>{error}</p>
      <button onClick={onBack} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', background: 'var(--primary)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', padding: '10px 24px', cursor: 'pointer' }}>← Back</button>
    </div>
  )

  const { client, metrics, opportunities, signals_summary, signals, proposals, feedback } = data
  const sig = signals_summary as Record<string, unknown>
  const propensityColor = client.propensity_tier === 'high' ? 'var(--status-green)' : client.propensity_tier === 'low' ? 'var(--mid)' : 'var(--gold)'
  const revenue = feedback.reduce((s, f) => s + ((f.revenue as number) || 0), 0)

  return (
    <div>
      {/* ── Hero ── */}
      <div style={hero}>
        <div style={wrap}>
          <button onClick={onBack} style={{ background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.45)', padding: 0, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 6 }}>
            ← Opportunities
          </button>

          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
            <div>
              <Eyebrow light>{client.industry}</Eyebrow>
              <h1 style={{ fontFamily: 'var(--fd)', fontSize: 32, fontWeight: 300, color: '#fff', margin: '4px 0 10px', lineHeight: 1.2 }}>
                {client.name}
                {client.is_demo_scenario ? <em style={{ fontStyle: 'normal', fontSize: 12, fontFamily: 'var(--fb)', color: 'var(--gold-light)', marginLeft: 12, letterSpacing: '2px', textTransform: 'uppercase' }}>DEMO</em> : null}
              </h1>
              <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
                <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>
                  Account manager: <strong style={{ color: 'rgba(255,255,255,0.85)' }}>{client.account_manager}</strong>
                </span>
                <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>
                  {client.contact_email}
                </span>
                <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>
                  Channel: <strong style={{ color: 'rgba(255,255,255,0.85)' }}>{client.preferred_channel}</strong>
                </span>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 300, color: 'var(--gold-light)' }}>
                ${(client.monthly_spend || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'rgba(255,255,255,0.4)', marginLeft: 4 }}>/mo</span>
              </div>
              {client.propensity_tier && (
                <span style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: propensityColor, background: `${propensityColor}20`, padding: '3px 10px', borderRadius: 'var(--radius-pill)', border: `1px solid ${propensityColor}40` }}>
                  {client.propensity_tier} propensity
                </span>
              )}
              <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
                Client for {client.account_age_days} days
              </span>
            </div>
          </div>
        </div>
      </div>

      <div style={{ backgroundColor: 'var(--light)' }}>
        <div style={body}>

          {/* ── KPI Metrics ── */}
          <section>
            <Eyebrow>Performance Metrics</Eyebrow>
            <h2 style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 16px' }}>
              Latest <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>data snapshot</em>
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
              <KpiCard label="Bounce Rate"       value={pct(metrics.bounce_rate)}        note="Target < 60%" />
              <KpiCard label="Conversion Rate"   value={pct(metrics.conversion_rate)}    note="Target > 2%" />
              <KpiCard label="Pages / Session"   value={fmt(metrics.pages_per_session)}  note="Target > 3" />
              <KpiCard label="Organic Traffic"   value={(metrics.organic_traffic ?? 0).toLocaleString()} note="Monthly visits" />
              <KpiCard label="CTR"               value={pct(metrics.ctr)}               note="Ad click-through" />
              <KpiCard label="ROAS"              value={`${fmt(metrics.roas)}×`}        note="Return on ad spend" />
              <KpiCard label="CPC"               value={`$${fmt(metrics.cpc, 2)}`}      note="Cost per click" />
              <KpiCard label="Ad Spend"          value={`$${fmt(metrics.ad_spend, 0)}`} note="Monthly" />
              <KpiCard label="Email Open Rate"   value={pct(metrics.email_open_rate)}   note="Target > 20%" />
              <KpiCard label="Email Click Rate"  value={pct(metrics.email_click_rate)}  note="Target > 2.5%" />
              <KpiCard label="Keyword Rankings"  value={String(metrics.keyword_rankings ?? '—')} note="Keywords ranked" />
              <KpiCard label="Days Inactive"     value={String(metrics.days_inactive ?? '—')}    note="In CRM" />
            </div>
          </section>

          {/* ── Opportunities ── */}
          <section>
            <Eyebrow>Detected Opportunities</Eyebrow>
            <h2 style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 16px' }}>
              {opportunities.length} active <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>
                {opportunities.length === 1 ? 'opportunity' : 'opportunities'}
              </em>
            </h2>
            {opportunities.length === 0 ? (
              <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>No opportunities detected for this client.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {opportunities.map((o, i) => {
                  const opp = o as Record<string, unknown>
                  const score    = (opp.score as number) ?? 0
                  const blended  = (opp.blended_score as number) ?? score
                  const seasonal = (opp.seasonal_boost as number) ?? 1
                  return (
                    <div key={i} style={{ ...card, padding: '20px 24px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                        <div>
                          <div style={{ fontFamily: 'var(--fb)', fontSize: 14, fontWeight: 700, color: 'var(--dark)', marginBottom: 4 }}>
                            {OPPORTUNITY_LABELS[opp.opportunity_type as string] ?? String(opp.label)}
                          </div>
                          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                            {(opp.triggered_signals as string[] ?? []).map(s => (
                              <code key={s} style={{ background: 'var(--primary-10)', color: 'var(--primary)', padding: '1px 7px', borderRadius: 4, fontSize: 10 }}>{s.replace(/_/g, ' ')}</code>
                            ))}
                            {seasonal > 1 && (
                              <span style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, color: '#e8c46a', background: 'rgba(200,152,42,0.12)', padding: '1px 7px', borderRadius: 4 }}>↑ {((seasonal - 1) * 100).toFixed(0)}% seasonal</span>
                            )}
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--gold)' }}>${(opp.suggested_price as number).toLocaleString()}</div>
                          {opp.ml_probability != null && (
                            <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)', marginTop: 2 }}>
                              ML: {((opp.ml_probability as number) * 100).toFixed(0)}% · Blended: {blended.toFixed(0)}
                            </div>
                          )}
                        </div>
                      </div>
                      <ScoreBar score={blended} />
                      <blockquote style={{ borderLeft: '2px solid var(--gold)', background: 'rgba(200,152,42,0.04)', padding: '8px 14px', borderRadius: '0 6px 6px 0', margin: '10px 0 0', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', fontStyle: 'italic' }}>
                        {String(opp.rationale)}
                      </blockquote>
                    </div>
                  )
                })}
              </div>
            )}
          </section>

          {/* ── Text Signals ── */}
          <section>
            <Eyebrow>Communication Signals</Eyebrow>
            <h2 style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 16px' }}>
              NLP <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>analysis</em>
            </h2>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
              <SignalFlag label="Churn Risk"      active={!!sig.churn_risk}      color="var(--status-red)" />
              <SignalFlag label="Urgency Signal"  active={!!sig.urgency_signal}  color="var(--status-orange)" />
              <SignalFlag label="Mentions Price"  active={!!sig.mentions_price}  color="var(--gold)" />
              <SignalFlag label="Asks for Results" active={!!sig.asks_for_results} color="var(--primary)" />
              <SignalFlag label="Interest Signal" active={!!sig.interest_signal} color="var(--status-green)" />
              {sig.sentiment_score != null && (
                <div style={{ padding: '6px 12px', background: 'var(--primary-10)', border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)' }}>
                  <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>Sentiment: </span>
                  <span style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 600, color: Number(sig.sentiment_score) > 0 ? 'var(--status-green)' : Number(sig.sentiment_score) < -0.1 ? 'var(--status-red)' : 'var(--mid)' }}>
                    {Number(sig.sentiment_score) > 0 ? '+' : ''}{Number(sig.sentiment_score).toFixed(2)}
                  </span>
                </div>
              )}
            </div>
            {signals.length > 0 && (
              <div style={{ ...card, padding: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 4 }}>
                  Recent Communications ({signals.length})
                </div>
                {signals.slice(0, 4).map((s, i) => {
                  const sig_r = s as Record<string, unknown>
                  const src   = (sig_r.source as string ?? 'email').replace(/_/g, ' ')
                  const text  = sig_r.raw_text as string ?? ''
                  return (
                    <div key={i} style={{ paddingBottom: 10, borderBottom: i < Math.min(signals.length, 4) - 1 ? '1px solid var(--primary-10)' : 'none' }}>
                      <div style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 4 }}>{src}</div>
                      <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)', fontStyle: 'italic', lineHeight: 1.5 }}>"{text.slice(0, 120)}{text.length > 120 ? '…' : ''}"</div>
                    </div>
                  )
                })}
              </div>
            )}
          </section>

          {/* ── Proposals ── */}
          <section>
            <Eyebrow>Proposal History</Eyebrow>
            <h2 style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 16px' }}>
              {proposals.length} {proposals.length === 1 ? 'proposal' : 'proposals'}{revenue > 0 ? ` · $${revenue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })} revenue realized` : ''}
            </h2>
            {proposals.length === 0 ? (
              <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>No proposals sent yet. Generate one from the Proposals page.</p>
            ) : (
              <div style={{ overflowX: 'auto', ...card }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      {['Opportunity', 'Subject', 'Status', 'Price', 'Sent'].map(h => (
                        <th key={h} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', padding: '10px 16px', color: '#fff', background: 'var(--primary)', textAlign: 'left', whiteSpace: 'nowrap' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {proposals.map((p, i) => (
                      <tr key={p.id} style={{ background: i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)', borderBottom: '1px solid var(--primary-10)' }}>
                        <td style={{ fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 16px', color: 'var(--dark)', fontWeight: 600 }}>
                          {OPPORTUNITY_LABELS[p.opportunity_type] ?? p.opportunity_type.replace(/_/g, ' ')}
                        </td>
                        <td style={{ fontFamily: 'var(--fb)', fontSize: 11, padding: '10px 16px', color: 'var(--mid)', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {p.subject}
                        </td>
                        <td style={{ padding: '10px 16px' }}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 600, color: STATUS_DOT[p.status] ?? 'var(--mid)' }}>
                            <span style={{ width: 6, height: 6, borderRadius: '50%', background: STATUS_DOT[p.status] ?? 'var(--mid)', flexShrink: 0 }} />
                            {p.status.charAt(0).toUpperCase() + p.status.slice(1)}
                          </span>
                        </td>
                        <td style={{ fontFamily: 'var(--fd)', fontSize: 16, fontWeight: 300, padding: '10px 16px', color: 'var(--gold)' }}>
                          ${p.suggested_price.toLocaleString()}
                        </td>
                        <td style={{ fontFamily: 'var(--fb)', fontSize: 11, padding: '10px 16px', color: 'var(--mid)', whiteSpace: 'nowrap' }}>
                          {p.sent_at ? p.sent_at.slice(0, 10) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

        </div>
      </div>
    </div>
  )
}
