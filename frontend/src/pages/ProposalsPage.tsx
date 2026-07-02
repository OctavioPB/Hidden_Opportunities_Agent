import { useState, useEffect } from 'react'
import Eyebrow from '../components/Eyebrow'
import { api, type Proposal } from '../services/api'

const OPPORTUNITY_LABELS: Record<string, string> = {
  landing_page_optimization: 'Landing Page Optimization',
  seo_content:               'SEO Content Package',
  retargeting_campaign:      'Retargeting Campaign',
  email_automation:          'Email Automation',
  reactivation:              'Express Reactivation',
  conversion_rate_audit:     'Conversion Rate Audit',
  upsell_ad_budget:          'Ad Budget Expansion',
}

const STATUS_LABELS: Record<string, string> = {
  draft:    'Draft',
  approved: 'Approved — Ready to Send',
  sent:     'Sent',
  rejected: 'Rejected',
  accepted: 'Accepted by Client',
}

const STATUS_COLORS: Record<string, { dot: string; bg: string; text: string }> = {
  draft:    { dot: '#f07020', bg: 'rgba(240,112,32,0.08)', text: '#7a3800' },
  approved: { dot: '#27b97c', bg: 'rgba(39,185,124,0.08)', text: '#0d5c3a' },
  sent:     { dot: '#003366', bg: 'rgba(0,51,102,0.08)',   text: '#001f4d' },
  rejected: { dot: '#e03448', bg: 'rgba(224,52,72,0.08)', text: '#7a1020' },
  accepted: { dot: '#27b97c', bg: 'rgba(39,185,124,0.08)', text: '#0d5c3a' },
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

function StatusBadge({ status }: { status: string }) {
  const c = STATUS_COLORS[status] ?? { dot: '#6b7280', bg: 'rgba(107,114,128,0.08)', text: '#374151' }
  const label = STATUS_LABELS[status] ?? status
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: c.bg, color: c.text, padding: '4px 12px', borderRadius: 'var(--radius-pill)', fontSize: 10, fontWeight: 600, fontFamily: 'var(--fb)', letterSpacing: '0.5px' }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: c.dot, display: 'inline-block', flexShrink: 0 }} />
      {label}
    </span>
  )
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 80 ? 'var(--status-green)' : score >= 60 ? 'var(--status-orange)' : 'var(--primary-60)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '8px 0' }}>
      <div style={{ flex: 1, background: 'var(--primary-10)', borderRadius: 4, height: 7, overflow: 'hidden' }}>
        <div style={{ width: `${score}%`, background: color, height: '100%', borderRadius: 4 }} />
      </div>
      <span style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700, color, minWidth: 40 }}>{score.toFixed(0)}/100</span>
    </div>
  )
}

function ProposalCard({ p, onRefresh }: { p: Proposal; onRefresh: () => void }) {
  const [editing,    setEditing]    = useState(false)
  const [editedBody, setEditedBody] = useState(p.body)
  const [msg,        setMsg]        = useState<string | null>(null)
  const [metrics,    setMetrics]    = useState<Record<string, number> | null>(null)

  useEffect(() => {
    api.proposals.metrics(p.id).then(setMetrics).catch(() => null)
  }, [p.id])

  const approve = async () => { await api.proposals.approve(p.id); setMsg('Approved.'); onRefresh() }
  const reject  = async () => { await api.proposals.reject(p.id);  setMsg('Rejected.'); onRefresh() }
  const revoke  = async () => { await api.proposals.revoke(p.id);  onRefresh() }
  const save    = async () => { await api.proposals.updateBody(p.id, editedBody); setEditing(false); onRefresh() }

  const label = OPPORTUNITY_LABELS[p.opportunity_type] ?? p.opportunity_type

  return (
    <div style={{ ...card, padding: 28 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 14, fontWeight: 600, color: 'var(--dark)' }}>
            {p.client_name}{p.is_demo_scenario ? ' [Demo]' : ''} &nbsp;·&nbsp;
            <span style={{ fontWeight: 400, fontStyle: 'italic', color: 'var(--mid)' }}>{p.industry}</span>
          </div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 600, color: 'var(--primary)', marginTop: 2 }}>{label}</div>
          <div style={{ marginTop: 6 }}><StatusBadge status={p.status} /></div>
        </div>
        <div style={{ fontFamily: 'var(--fd)', fontSize: 24, fontWeight: 300, color: 'var(--gold)', flexShrink: 0 }}>
          ${p.suggested_price.toLocaleString()}
        </div>
      </div>

      <ScoreBar score={p.score ?? 0} />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginTop: 16 }}>
        {/* Opportunity data */}
        <div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 600, color: 'var(--dark)', marginBottom: 8 }}>Opportunity Data</div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginBottom: 4 }}>Raw signals that triggered this proposal</div>
          {metrics ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {Object.entries({
                CTR:              metrics.ctr != null ? `${(metrics.ctr * 100).toFixed(1)}%` : null,
                'Bounce Rate':    metrics.bounce_rate != null ? `${(metrics.bounce_rate * 100).toFixed(0)}%` : null,
                'Pages/Session':  metrics.pages_per_session != null ? metrics.pages_per_session.toFixed(1) : null,
                'Conv. Rate':     metrics.conversion_rate != null ? `${(metrics.conversion_rate * 100).toFixed(2)}%` : null,
                'Ad Spend/mo':    metrics.ad_spend > 0 ? `$${metrics.ad_spend.toLocaleString()}` : null,
                'ROAS':           metrics.roas > 0 ? `${metrics.roas.toFixed(1)}x` : null,
                'Email Open':     metrics.email_open_rate > 0 ? `${(metrics.email_open_rate * 100).toFixed(1)}%` : null,
                'Days Inactive':  metrics.days_inactive > 0 ? String(metrics.days_inactive) : null,
              }).filter(([, v]) => v !== null).map(([k, v]) => (
                <div key={k} style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)' }}>
                  <strong style={{ color: 'var(--mid)' }}>{k}:</strong> {v}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>Loading metrics…</div>
          )}
        </div>

        {/* Proposal preview */}
        <div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 600, color: 'var(--dark)', marginBottom: 8 }}>Proposal Preview</div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginBottom: 8 }}>Email that will be sent to the client</div>
          {editing ? (
            <div>
              <textarea
                value={editedBody}
                onChange={e => setEditedBody(e.target.value)}
                rows={8}
                style={{ width: '100%', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)', border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: 10, resize: 'vertical' }}
              />
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button onClick={save} style={primaryBtn}>Save</button>
                <button onClick={() => setEditing(false)} style={secondaryBtn}>Cancel</button>
              </div>
            </div>
          ) : (
            <div style={{ border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: 14, background: 'var(--light)' }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 600, color: 'var(--dark)', marginBottom: 8 }}>Subject: {p.subject}</div>
              <div style={{ width: '100%', height: 1, background: 'var(--primary-10)', marginBottom: 10 }} />
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', whiteSpace: 'pre-wrap', maxHeight: 200, overflowY: 'auto' }}>{p.body}</div>
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      {msg && <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--status-green)', marginTop: 12 }}>{msg}</div>}
      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        {p.status === 'draft' && !editing && (
          <>
            <button onClick={approve} style={primaryBtn}>Approve</button>
            <button onClick={() => setEditing(true)} style={secondaryBtn}>Edit</button>
            <button onClick={reject} style={{ ...secondaryBtn, color: 'var(--status-red)' }}>Reject</button>
          </>
        )}
        {p.status === 'approved' && (
          <button onClick={revoke} style={secondaryBtn}>Revoke Approval</button>
        )}
      </div>
    </div>
  )
}

const primaryBtn: React.CSSProperties = {
  fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px',
  textTransform: 'uppercase', backgroundColor: 'var(--gold)', color: '#fff',
  border: 'none', borderRadius: 'var(--radius-sm)', padding: '8px 16px', cursor: 'pointer',
}
const secondaryBtn: React.CSSProperties = {
  fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px',
  textTransform: 'uppercase', background: 'none', color: 'var(--mid)',
  border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: '8px 16px', cursor: 'pointer',
}

function FollowUpQueuePanel() {
  const [queue,      setQueue]      = useState<Record<string, unknown>[]>([])
  const [processing, setProcessing] = useState(false)
  const [msg,        setMsg]        = useState<string | null>(null)

  useEffect(() => { api.followUps.list().then(setQueue) }, [])

  const processDue = async () => {
    setProcessing(true)
    const res = await api.followUps.process()
    setMsg(`Processed ${res.processed} due follow-up(s).`)
    api.followUps.list().then(setQueue)
    setProcessing(false)
  }

  const cancel = async (id: string) => {
    await api.followUps.cancel(id)
    api.followUps.list().then(setQueue)
  }

  const pending = queue.filter(q => q.status === 'pending')
  const sent    = queue.filter(q => q.status === 'sent')

  const statusColor = (s: string) => s === 'pending' ? 'var(--status-orange)' : s === 'sent' ? 'var(--status-green)' : 'var(--mid)'
  const statusBg    = (s: string) => s === 'pending' ? 'rgba(240,112,32,0.08)' : s === 'sent' ? 'rgba(39,185,124,0.08)' : 'rgba(107,114,128,0.08)'

  const th: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', padding: '10px 14px', color: '#fff', background: 'var(--primary)', textAlign: 'left' }
  const td: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 12, padding: '9px 14px', color: 'var(--dark)' }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>
          <strong style={{ color: 'var(--dark)' }}>{pending.length}</strong> pending · <strong style={{ color: 'var(--status-green)' }}>{sent.length}</strong> sent
        </div>
        <button onClick={processDue} disabled={processing} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', backgroundColor: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', padding: '8px 16px', cursor: processing ? 'wait' : 'pointer', marginLeft: 'auto' }}>
          {processing ? 'Processing…' : 'Process Due Now'}
        </button>
      </div>
      {msg && <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--status-green)' }}>{msg}</div>}

      {queue.length === 0 ? (
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>
          No follow-ups scheduled yet. They are created automatically when a client ignores a proposal.
        </p>
      ) : (
        <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', border: '1px solid var(--primary-10)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>{['Client', 'Turn', 'Angle', 'Scheduled', 'Status', ''].map(h => <th key={h} style={th}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {queue.map((q, i) => (
                <tr key={q.id as string} style={{ background: i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)', borderBottom: '1px solid var(--primary-10)' }}>
                  <td style={{ ...td, fontWeight: 600 }}>{q.client_name as string}</td>
                  <td style={{ ...td, textAlign: 'center' }}>{q.sequence_turn as number}</td>
                  <td style={{ ...td, color: 'var(--mid)', fontStyle: 'italic' }}>{(q.angle as string ?? '').replace('_', ' ')}</td>
                  <td style={{ ...td, color: 'var(--mid)' }}>{(q.scheduled_at as string ?? '').slice(0, 10)}</td>
                  <td style={td}>
                    <span style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700, color: statusColor(q.status as string), background: statusBg(q.status as string), padding: '2px 8px', borderRadius: 'var(--radius-pill)' }}>
                      {q.status as string}
                    </span>
                  </td>
                  <td style={td}>
                    {q.status === 'pending' && (
                      <button onClick={() => cancel(q.id as string)} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase', background: 'none', color: 'var(--mid)', border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: '3px 8px', cursor: 'pointer' }}>
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default function ProposalsPage() {
  const [proposals,   setProposals]   = useState<Proposal[]>([])
  const [loading,     setLoading]     = useState(true)
  const [generating,  setGenerating]  = useState(false)
  const [selStatus,   setSelStatus]   = useState('All')
  const [selType,     setSelType]     = useState('All')
  const [demoOnly,    setDemoOnly]    = useState(false)
  const [view,        setView]        = useState<'Cards' | 'Log' | 'Follow-Ups' | 'CRM'>('Cards')
  const [minScore,    setMinScore]    = useState(70)
  const [genMsg,      setGenMsg]      = useState<string | null>(null)
  const [showGenerate, setShowGenerate] = useState(false)
  const [crmLog,      setCrmLog]      = useState<Record<string, unknown>[]>([])

  const reload = () => {
    setLoading(true)
    api.proposals.list().then(setProposals).finally(() => setLoading(false))
  }

  useEffect(() => { reload() }, [])
  useEffect(() => {
    if (view === 'CRM') api.crm.log().then(setCrmLog)
  }, [view])

  const filtered = proposals.filter(p =>
    (selStatus === 'All' || p.status === selStatus) &&
    (selType === 'All' || p.opportunity_type === selType) &&
    (!demoOnly || p.is_demo_scenario)
  )

  const sortPriority: Record<string, number> = { draft: 0, approved: 1, sent: 2, accepted: 3, rejected: 4 }
  const sorted = [...filtered].sort((a, b) =>
    (sortPriority[a.status] ?? 5) - (sortPriority[b.status] ?? 5) || (b.score ?? 0) - (a.score ?? 0)
  )

  const statuses    = ['All', ...new Set(proposals.map(p => p.status))]
  const oppTypes    = ['All', ...new Set(proposals.map(p => p.opportunity_type))]
  const draft       = proposals.filter(p => p.status === 'draft').length
  const approved    = proposals.filter(p => p.status === 'approved').length
  const sent        = proposals.filter(p => ['sent', 'accepted'].includes(p.status)).length
  const totalValue  = proposals.filter(p => p.status !== 'rejected').reduce((s, p) => s + p.suggested_price, 0)

  const generateAll = async () => {
    setGenerating(true); setGenMsg(null)
    const res = await api.proposals.generateAll(minScore)
    setGenMsg(`Generated ${res.generated} new proposal(s).`)
    reload()
    setGenerating(false)
  }

  const selectStyle: React.CSSProperties = {
    fontFamily: 'var(--fb)', fontSize: 13, color: '#1c1c2e',
    border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)',
    padding: '8px 12px', backgroundColor: '#fff', cursor: 'pointer',
    colorScheme: 'light',
  }
  const tabBtn = (active: boolean): React.CSSProperties => ({
    background: 'none', border: 'none', cursor: 'pointer',
    fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 500,
    letterSpacing: '1.5px', textTransform: 'uppercase',
    padding: '8px 20px', marginBottom: -1,
    borderBottom: `2px solid ${active ? 'var(--gold)' : 'transparent'}`,
    color: active ? 'var(--gold)' : 'var(--mid)', transition: 'color 0.15s',
  })

  const th: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', padding: '11px 14px', color: '#fff', background: 'var(--primary)', textAlign: 'left' }
  const td: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 14px', color: 'var(--dark)' }

  return (
    <div>
      <div style={hero}>
        <div style={wrap}>
          <Eyebrow light>Deal Pipeline</Eyebrow>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: '#fff', margin: '0 0 6px', lineHeight: 1.2 }}>
            Proposal Review <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>&amp; Approval</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'rgba(255,255,255,0.45)', margin: '0 0 32px' }}>
            Human-in-the-loop approval workflow · AI writes, you approve
          </p>
          <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
            {[
              { value: String(proposals.length), label: 'Total Proposals' },
              { value: String(draft),            label: 'Drafts Pending' },
              { value: String(approved),         label: 'Approved' },
              { value: String(sent),             label: 'Sent / Accepted' },
              { value: `$${totalValue.toLocaleString()}`, label: 'Pipeline Value' },
            ].map(s => (
              <div key={s.label} style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18 }}>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 32, fontWeight: 300, color: 'var(--gold-light)', lineHeight: 1 }}>{s.value}</div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ backgroundColor: 'var(--light)' }}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto', padding: '44px 48px', display: 'flex', flexDirection: 'column', gap: 32 }}>

          {/* Generate panel */}
          <div style={{ ...card, padding: 24 }}>
            <button onClick={() => setShowGenerate(g => !g)} style={{ ...secondaryBtn, marginBottom: showGenerate ? 16 : 0 }}>
              {showGenerate ? '▾' : '▸'} Generate Proposals On-Demand
            </button>
            {showGenerate && (
              <div>
                <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginBottom: 12 }}>
                  Generate proposals for all detected opportunities with score ≥ threshold that don't yet have a draft.
                </p>
                <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end', flexWrap: 'wrap' }}>
                  <div>
                    <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>
                      Min Score: {minScore}
                    </label>
                    <input type="range" min={50} max={100} step={5} value={minScore} onChange={e => setMinScore(Number(e.target.value))} style={{ width: 200, accentColor: 'var(--gold)' }} />
                  </div>
                  <button onClick={generateAll} disabled={generating} style={primaryBtn}>{generating ? 'Generating…' : 'Generate All Above Threshold'}</button>
                </div>
                {genMsg && <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--status-green)', marginTop: 10 }}>{genMsg}</div>}
              </div>
            )}
          </div>

          {/* Filters */}
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div>
              <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>Status</label>
              <select style={selectStyle} value={selStatus} onChange={e => setSelStatus(e.target.value)}>
                {statuses.map(s => <option key={s} value={s}>{s === 'All' ? 'All Statuses' : STATUS_LABELS[s] ?? s}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>Opportunity Type</label>
              <select style={selectStyle} value={selType} onChange={e => setSelType(e.target.value)}>
                {oppTypes.map(t => <option key={t} value={t}>{t === 'All' ? 'All Types' : OPPORTUNITY_LABELS[t] ?? t}</option>)}
              </select>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', cursor: 'pointer', paddingBottom: 2 }}>
              <input type="checkbox" checked={demoOnly} onChange={e => setDemoOnly(e.target.checked)} />
              Demo clients only
            </label>
          </div>

          {/* View toggle */}
          <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--primary-10)' }}>
            <button style={tabBtn(view === 'Cards')}      onClick={() => setView('Cards')}>Cards</button>
            <button style={tabBtn(view === 'Log')}         onClick={() => setView('Log')}>Log</button>
            <button style={tabBtn(view === 'Follow-Ups')} onClick={() => setView('Follow-Ups')}>Follow-Ups</button>
            <button style={tabBtn(view === 'CRM')}         onClick={() => setView('CRM')}>CRM Sync</button>
          </div>

          {loading && <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>Loading proposals…</p>}

          {!loading && proposals.length === 0 && (
            <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>No proposals yet. Use the Generate panel above to create them.</p>
          )}

          {!loading && view === 'Cards' && sorted.map(p => (
            <ProposalCard key={p.id} p={p} onRefresh={reload} />
          ))}

          {!loading && view === 'Log' && sorted.length > 0 && (
            <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', border: '1px solid var(--primary-10)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    {['Client', 'Opportunity', 'Score', 'Price', 'Status', 'Created'].map(h => <th key={h} style={th}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((p, i) => (
                    <tr key={p.id} style={{ background: i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)', borderBottom: '1px solid var(--primary-10)' }}>
                      <td style={{ ...td, fontWeight: 600 }}>{p.client_name}</td>
                      <td style={td}>{OPPORTUNITY_LABELS[p.opportunity_type] ?? p.opportunity_type}</td>
                      <td style={td}>{(p.score ?? 0).toFixed(0)}</td>
                      <td style={{ ...td, color: 'var(--gold)' }}>${p.suggested_price.toLocaleString()}</td>
                      <td style={td}><StatusBadge status={p.status} /></td>
                      <td style={{ ...td, color: 'var(--mid)' }}>{(p.created_at || '').slice(0, 10)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Feature 1 — Follow-Up Queue */}
          {!loading && view === 'Follow-Ups' && (
            <section>
              <Eyebrow>Follow-Up Sequences</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
                Scheduled <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>follow-up queue</em>
              </h2>
              <FollowUpQueuePanel />
            </section>
          )}

          {/* Feature 5 — CRM Sync Log */}
          {!loading && view === 'CRM' && (
            <section>
              <Eyebrow>CRM Write-Back</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 8px' }}>
                HubSpot <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>sync log</em>
              </h2>
              <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginBottom: 20 }}>
                In demo mode, CRM syncs are logged here instead of calling the HubSpot API.
                Each accepted proposal triggers an automatic deal creation.
              </p>
              {crmLog.length === 0 ? (
                <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>
                  No CRM syncs yet. Accept a proposal to trigger the first sync.
                </p>
              ) : (
                <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', border: '1px solid var(--primary-10)' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>{['Action', 'Client', 'Proposal', 'Revenue', 'Synced At'].map(h => <th key={h} style={th}>{h}</th>)}</tr>
                    </thead>
                    <tbody>
                      {crmLog.map((r, i) => (
                        <tr key={i} style={{ background: i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)', borderBottom: '1px solid var(--primary-10)' }}>
                          <td style={td}>
                            <span style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700, color: 'var(--status-green)', background: 'rgba(39,185,124,0.08)', padding: '2px 8px', borderRadius: 'var(--radius-pill)' }}>
                              {r.action as string}
                            </span>
                          </td>
                          <td style={{ ...td, fontWeight: 600 }}>{(r.client_id as string ?? '').slice(0, 8)}…</td>
                          <td style={{ ...td, color: 'var(--mid)' }}>{(r.proposal_id as string ?? '').slice(0, 8)}…</td>
                          <td style={{ ...td, color: 'var(--gold)', fontFamily: 'var(--fd)', fontSize: 14, fontWeight: 300 }}>
                            {r.revenue != null ? `$${(r.revenue as number).toLocaleString()}` : '—'}
                          </td>
                          <td style={{ ...td, color: 'var(--mid)' }}>{(r.synced_at as string ?? '').slice(0, 16).replace('T', ' ')}</td>
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
