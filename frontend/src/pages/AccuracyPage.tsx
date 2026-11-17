import { useState, useEffect } from 'react'
import Eyebrow from '../components/Eyebrow'
import { api, type AccuracyRow, type AccuracyMetrics } from '../services/api'

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

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ ...card, padding: 28, display: 'flex', alignItems: 'stretch', gap: 16 }}>
      <div style={{ width: 3, backgroundColor: 'var(--gold)', borderRadius: 2, flexShrink: 0 }} />
      <div>
        <div style={{ fontFamily: 'var(--fd)', fontSize: 30, fontWeight: 300, color: 'var(--dark)' }}>{value}</div>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '3px', color: 'var(--mid)', marginTop: 5 }}>{label}</div>
      </div>
    </div>
  )
}

function RecallBar({ recall }: { recall: number }) {
  const pct   = recall * 100
  const color = pct >= 80 ? 'var(--status-green)' : pct >= 60 ? 'var(--status-orange)' : 'var(--status-red)'
  const tier  = pct >= 80 ? 'MEETS TARGET' : 'BELOW TARGET'
  return (
    <div style={{ margin: '6px 0 10px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ flex: 1, background: 'var(--primary-10)', borderRadius: 4, height: 7, overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, background: color, height: '100%', borderRadius: 4, transition: 'width 0.4s' }} />
        </div>
        <span style={{
          fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700, letterSpacing: '0.8px',
          textTransform: 'uppercase', color, padding: '3px 11px',
          borderRadius: 'var(--radius-pill)', minWidth: 140, textAlign: 'center',
        }}>
          {tier} &nbsp;{pct.toFixed(1)}%
        </span>
      </div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)', marginTop: 3 }}>Target: 80%+</div>
    </div>
  )
}

export default function AccuracyPage() {
  const [rows,    setRows]    = useState<AccuracyRow[]>([])
  const [metrics, setMetrics] = useState<AccuracyMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  useEffect(() => {
    api.accuracy.get()
      .then(d => { setRows(d.rows); setMetrics(d.metrics) })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>Loading accuracy data…</p>
    </div>
  )

  if (error || !metrics) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
      <div style={{ textAlign: 'center' }}>
        <p style={{ fontFamily: 'var(--fd)', fontSize: 18, color: 'var(--status-orange)', marginBottom: 6 }}>Could not load data.</p>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>{error} — ensure the backend is running.</p>
      </div>
    </div>
  )

  const th: React.CSSProperties = {
    fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '2px',
    textTransform: 'uppercase', padding: '11px 14px', color: '#fff',
    background: 'var(--primary)', textAlign: 'left',
  }
  const td: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 14px' }

  const statusColor = (s: string) => s === 'Perfect' ? 'var(--status-green)' : s === 'Extra' ? 'var(--status-orange)' : 'var(--status-red)'
  const statusBg    = (s: string) => s === 'Perfect' ? 'rgba(39,185,124,0.08)' : s === 'Extra' ? 'rgba(240,112,32,0.08)' : 'rgba(224,52,72,0.08)'

  return (
    <div>
      <div style={hero}>
        <div style={wrap}>
          <Eyebrow light>Analytics</Eyebrow>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: '#fff', margin: '0 0 6px', lineHeight: 1.2 }}>
            Detection <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Accuracy</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'rgba(255,255,255,0.45)', margin: '0 0 32px' }}>
            Validation against 10 manually labeled test clients · measures rule engine performance
          </p>
          <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
            {[
              { value: `${(metrics.precision * 100).toFixed(1)}%`, label: 'Precision' },
              { value: `${(metrics.recall * 100).toFixed(1)}%`,    label: 'Recall' },
              { value: `${(metrics.f1 * 100).toFixed(1)}%`,        label: 'F1 Score' },
              { value: String(rows.length),                        label: 'Test Clients' },
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

          {/* KPI cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
            <KpiCard label="Precision" value={`${(metrics.precision * 100).toFixed(1)}%`} />
            <KpiCard label="Recall"    value={`${(metrics.recall * 100).toFixed(1)}%`} />
            <KpiCard label="F1 Score"  value={`${(metrics.f1 * 100).toFixed(1)}%`} />
            <KpiCard label="Test Clients" value={String(rows.length)} />
          </div>

          {/* Recall vs target */}
          <section>
            <Eyebrow>Recall Performance</Eyebrow>
            <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 16px' }}>
              Recall vs. <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>target</em>
            </h2>
            <div style={{ ...card, padding: 28 }}>
              <p style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 600, color: 'var(--dark)', marginBottom: 10 }}>Recall vs. target (80%)</p>
              <RecallBar recall={metrics.recall} />
              <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: metrics.recall >= 0.8 ? 'var(--status-green)' : 'var(--status-orange)', marginTop: 10 }}>
                {metrics.recall >= 0.8
                  ? `Recall ${(metrics.recall * 100).toFixed(1)}% — meets the target of 80%.`
                  : `Recall ${(metrics.recall * 100).toFixed(1)}% — below the target of 80%. Consider lowering detection thresholds.`}
              </p>
            </div>
          </section>

          {/* Per-client table */}
          <section>
            <Eyebrow>Per-Client Results</Eyebrow>
            <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
              Individual <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>breakdown</em>
            </h2>
            <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', border: '1px solid var(--primary-10)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    {['Client', 'Expected', 'Detected', 'TP', 'FP', 'FN', 'Status'].map(h => (
                      <th key={h} style={th}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i} style={{ background: i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)', borderBottom: '1px solid var(--primary-10)' }}>
                      <td style={{ ...td, fontWeight: 600, color: 'var(--dark)' }}>{r.client}</td>
                      <td style={{ ...td, color: 'var(--mid)' }}>{r.expected}</td>
                      <td style={{ ...td, color: 'var(--mid)' }}>{r.detected}</td>
                      <td style={{ ...td, textAlign: 'center' }}>{r.tp}</td>
                      <td style={{ ...td, textAlign: 'center', color: r.fp > 0 ? 'var(--status-orange)' : 'var(--dark)' }}>{r.fp}</td>
                      <td style={{ ...td, textAlign: 'center', color: r.fn > 0 ? 'var(--status-red)' : 'var(--dark)' }}>{r.fn}</td>
                      <td style={{ ...td }}>
                        <span style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700, color: statusColor(r.status), background: statusBg(r.status), padding: '2px 9px', borderRadius: 'var(--radius-pill)' }}>
                          {r.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Confusion summary */}
          <section>
            <Eyebrow>Confusion Summary</Eyebrow>
            <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
              Aggregate <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>counts</em>
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
              {[
                { label: 'True Positives',  value: metrics.tp, note: 'Correctly detected',        color: 'var(--status-green)' },
                { label: 'False Positives', value: metrics.fp, note: 'Detected but shouldn\'t',    color: 'var(--status-orange)' },
                { label: 'False Negatives', value: metrics.fn, note: 'Missed real opportunities',  color: 'var(--status-red)' },
              ].map(({ label, value, note, color }) => (
                <div key={label} style={{ ...card, padding: 24 }}>
                  <div style={{ fontFamily: 'var(--fd)', fontSize: 36, fontWeight: 300, color }}>{value}</div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '2px', color: 'var(--mid)', marginTop: 6 }}>{label}</div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginTop: 4 }}>{note}</div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
