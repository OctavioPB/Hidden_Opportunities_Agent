import { useState, useEffect } from 'react'
import Eyebrow from '../components/Eyebrow'
import { api, type MLStatus, type MLPrediction } from '../services/api'

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

// ── Feature importance horizontal bar chart (hand-coded SVG) ──────────────────
function FeatureImportanceChart({ data }: { data: { name: string; label: string; importance: number }[] }) {
  if (!data.length) return <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>No feature data.</p>

  const top     = data.slice(0, 10)
  const maxVal  = Math.max(...top.map(f => f.importance))
  const ROW_H   = 32
  const PAD_L   = 180
  const BAR_W   = 320
  const PAD_R   = 60
  const W       = PAD_L + BAR_W + PAD_R
  const H       = top.length * ROW_H + 20

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
      {top.map((f, i) => {
        const bw    = maxVal > 0 ? (f.importance / maxVal) * BAR_W : 0
        const y     = i * ROW_H + ROW_H / 2
        const color = f.importance >= maxVal * 0.6 ? '#27b97c' : f.importance >= maxVal * 0.3 ? '#c8982a' : '#99bbdd'
        return (
          <g key={f.name}>
            <text x={PAD_L - 8} y={y + 4} fontSize={10} fill="#6b7280" textAnchor="end" fontFamily="'Plus Jakarta Sans',sans-serif">
              {f.label.length > 22 ? f.label.slice(0, 21) + '…' : f.label}
            </text>
            <rect x={PAD_L} y={y - 10} width={BAR_W} height={20} fill="rgba(0,51,102,0.04)" rx={3} />
            <rect x={PAD_L} y={y - 10} width={Math.max(3, bw)} height={20} fill={color} rx={3} opacity={0.82} />
            <text x={PAD_L + bw + 6} y={y + 4} fontSize={9} fill={color} fontFamily="'Plus Jakarta Sans',sans-serif" fontWeight="700">
              {f.importance.toFixed(4)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

export default function MLModelPage() {
  const [status,      setStatus]      = useState<MLStatus | null>(null)
  const [predictions, setPredictions] = useState<MLPrediction[]>([])
  const [importance,  setImportance]  = useState<{ name: string; label: string; importance: number }[]>([])
  const [summary,     setSummary]     = useState<{ total_predictions: number; high_prob_count: number; avg_ml_probability: number | null } | null>(null)
  const [loading,     setLoading]     = useState(true)
  const [training,    setTraining]    = useState(false)
  const [trainMsg,    setTrainMsg]    = useState<string | null>(null)
  const [activeTab,   setActiveTab]   = useState<'Model Card' | 'Features' | 'Predictions' | 'Explain'>('Model Card')
  const [selExplain,  setSelExplain]  = useState<string>('')

  const reload = () => {
    setLoading(true)
    Promise.all([
      api.ml.status(),
      api.ml.predictions(),
      api.ml.featureImportance(),
      api.ml.summary(),
    ]).then(([s, p, fi, sm]) => {
      setStatus(s)
      setPredictions(p)
      setImportance(fi)
      setSummary(sm)
      if (p.length > 0 && !selExplain) setSelExplain(`${p[0].client_name} — ${OPPORTUNITY_LABELS[p[0].opportunity_type] ?? p[0].opportunity_type}`)
    }).finally(() => setLoading(false))
  }

  useEffect(() => { reload() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const train = async () => {
    setTraining(true); setTrainMsg(null)
    try {
      const res = await api.ml.train()
      const met = (res as Record<string, unknown>).metrics as Record<string, number> | undefined
      setTrainMsg(met ? `Model trained! AUC-ROC: ${met.auc_roc?.toFixed(4)}` : 'Model trained successfully.')
      reload()
    } catch (e) {
      setTrainMsg(`Training failed: ${e}`)
    }
    setTraining(false)
  }

  const meta = status?.metadata

  const tabs: ('Model Card' | 'Features' | 'Predictions' | 'Explain')[] = ['Model Card', 'Features', 'Predictions', 'Explain']
  const tabBtn = (t: string): React.CSSProperties => ({
    background: 'none', border: 'none', cursor: 'pointer',
    fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 500,
    letterSpacing: '1.5px', textTransform: 'uppercase',
    padding: '10px 20px', marginBottom: -1,
    borderBottom: `2px solid ${activeTab === t ? 'var(--gold-light)' : 'transparent'}`,
    color: activeTab === t ? 'var(--gold-light)' : 'rgba(255,255,255,0.4)',
    transition: 'color 0.15s',
  })

  const th: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', padding: '11px 14px', color: '#fff', background: 'var(--primary)', textAlign: 'left' }
  const td: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 14px', color: 'var(--dark)' }

  const explainPred = predictions.find(p =>
    `${p.client_name} — ${OPPORTUNITY_LABELS[p.opportunity_type] ?? p.opportunity_type}` === selExplain
  )

  return (
    <div>
      {/* ── Hero with tab bar ── */}
      <div style={{ ...hero, padding: '52px 48px 0' }}>
        <div style={wrap}>
          <Eyebrow light>Intelligence</Eyebrow>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: '#fff', margin: '0 0 6px', lineHeight: 1.2 }}>
            ML Model — <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Predictive Analyst</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'rgba(255,255,255,0.45)', marginBottom: 32 }}>
            Rule-based scores blended with ML acceptance probabilities · RandomForest classifier
          </p>

          {!loading && status?.is_trained && summary && (
            <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap', marginBottom: 32 }}>
              {[
                { value: meta?.metrics.auc_roc.toFixed(4) ?? '—',  label: 'AUC-ROC' },
                { value: String(summary.total_predictions),          label: 'Predictions Run' },
                { value: String(summary.high_prob_count),            label: 'High Prob (≥70%)' },
                { value: summary.avg_ml_probability != null ? `${(summary.avg_ml_probability * 100).toFixed(0)}%` : '—', label: 'Avg ML Probability' },
              ].map(s => (
                <div key={s.label} style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18 }}>
                  <div style={{ fontFamily: 'var(--fd)', fontSize: 32, fontWeight: 300, color: 'var(--gold-light)', lineHeight: 1 }}>{s.value}</div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>{s.label}</div>
                </div>
              ))}
            </div>
          )}

          {/* Tab bar */}
          <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid rgba(255,255,255,0.1)', marginTop: 8 }}>
            {tabs.map(t => <button key={t} style={tabBtn(t)} onClick={() => setActiveTab(t)}>{t}</button>)}
          </div>
        </div>
      </div>

      {/* ── Body ── */}
      <div style={{ backgroundColor: 'var(--light)' }}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto', padding: '44px 48px', display: 'flex', flexDirection: 'column', gap: 32 }}>

          {/* Retrain panel */}
          <div style={{ ...card, padding: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
            <div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)' }}>
                {status?.is_trained
                  ? `Model trained at ${(meta?.trained_at ?? '').slice(0, 16).replace('T', ' ')}. Click to retrain on latest data.`
                  : 'No model trained yet. Click to train on the current dataset.'}
              </div>
              {trainMsg && <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--status-green)', marginTop: 6 }}>{trainMsg}</div>}
            </div>
            <button onClick={train} disabled={training} style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', backgroundColor: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', padding: '10px 24px', cursor: training ? 'wait' : 'pointer', opacity: training ? 0.7 : 1, flexShrink: 0 }}>
              {training ? 'Training…' : 'Retrain Model'}
            </button>
          </div>

          {loading && <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>Loading model data…</p>}

          {!loading && !status?.is_trained && (
            <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>No trained model found. Click Retrain Model above to train the RandomForest (10–30 seconds).</p>
          )}

          {/* Tab content */}
          {!loading && status?.is_trained && activeTab === 'Model Card' && meta && (
            <section>
              <Eyebrow>Model Card</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
                Training <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>metrics</em>
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16 }}>
                {[
                  { label: 'AUC-ROC',       value: meta.metrics.auc_roc.toFixed(4) },
                  { label: 'Avg Precision',  value: meta.metrics.avg_precision.toFixed(4) },
                  { label: 'Precision',      value: meta.metrics.precision.toFixed(4) },
                  { label: 'Recall',         value: meta.metrics.recall.toFixed(4) },
                  { label: 'F1 Score',       value: meta.metrics.f1.toFixed(4) },
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
              <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginTop: 16 }}>
                Trained: <strong style={{ color: 'var(--dark)' }}>{meta.trained_at.slice(0, 16).replace('T', ' ')}</strong> · Samples: <strong style={{ color: 'var(--dark)' }}>{meta.n_samples.toLocaleString()}</strong> · Features: <strong style={{ color: 'var(--dark)' }}>{meta.n_features}</strong> · CV folds: <strong style={{ color: 'var(--dark)' }}>{meta.cv_folds}</strong> · Algorithm: RandomForestClassifier
              </p>
            </section>
          )}

          {!loading && status?.is_trained && activeTab === 'Features' && (
            <section>
              <Eyebrow>Feature Importance</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 8px' }}>
                Global <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>importance</em>
              </h2>
              <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginBottom: 20 }}>
                Higher importance = more influence on the acceptance probability prediction.
              </p>
              <div style={{ ...card, padding: 28 }}>
                <FeatureImportanceChart data={importance} />
              </div>
            </section>
          )}

          {!loading && status?.is_trained && activeTab === 'Predictions' && (
            <section>
              <Eyebrow>ML Predictions</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 8px' }}>
                All <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>clients</em>
              </h2>
              <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginBottom: 20 }}>
                Rule score (heuristic) vs. ML probability (model) vs. blended score (0.55 × ML + 0.45 × rule).
              </p>
              <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', border: '1px solid var(--primary-10)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      {['Client', 'Industry', 'Opportunity', 'Rule Score', 'ML Prob', 'Blended', 'Price'].map(h => <th key={h} style={th}>{h}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {predictions.map((p, i) => (
                      <tr key={i} style={{ background: i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)', borderBottom: '1px solid var(--primary-10)' }}>
                        <td style={{ ...td, fontWeight: 600 }}>{p.client_name}</td>
                        <td style={{ ...td, color: 'var(--mid)' }}>{p.industry}</td>
                        <td style={td}>{OPPORTUNITY_LABELS[p.opportunity_type] ?? p.opportunity_type}</td>
                        <td style={{ ...td, color: p.rule_score >= 80 ? 'var(--status-green)' : p.rule_score >= 60 ? 'var(--status-orange)' : 'var(--dark)' }}>{p.rule_score.toFixed(0)}</td>
                        <td style={{ ...td, color: 'var(--status-purple)' }}>{p.ml_probability != null ? `${(p.ml_probability * 100).toFixed(0)}%` : '—'}</td>
                        <td style={{ ...td, fontWeight: 600 }}>{p.blended_score.toFixed(1)}</td>
                        <td style={{ ...td, color: 'var(--gold)' }}>${p.suggested_price.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {!loading && status?.is_trained && activeTab === 'Explain' && (
            <section>
              <Eyebrow>Why This Opportunity?</Eyebrow>
              <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 16px' }}>
                SHAP <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>feature contributions</em>
              </h2>
              <div style={{ marginBottom: 20 }}>
                <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6 }}>Select Opportunity</label>
                <select
                  value={selExplain}
                  onChange={e => setSelExplain(e.target.value)}
                  style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', backgroundColor: 'var(--white)', cursor: 'pointer', minWidth: 360 }}
                >
                  {predictions.slice(0, 20).map(p => {
                    const key = `${p.client_name} — ${OPPORTUNITY_LABELS[p.opportunity_type] ?? p.opportunity_type}`
                    return <option key={key} value={key}>{key}</option>
                  })}
                </select>
              </div>

              {explainPred?.explanation ? (
                <div style={{ ...card, padding: 28 }}>
                  <div style={{ borderLeft: `3px solid ${explainPred.explanation.probability >= 0.7 ? '#27b97c' : explainPred.explanation.probability >= 0.5 ? '#c8982a' : '#e03448'}`, background: 'var(--light)', borderRadius: '0 var(--radius-sm) var(--radius-sm) 0', padding: '12px 16px', marginBottom: 20 }}>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 13, lineHeight: 1.7, color: 'var(--dark)' }}>{explainPred.explanation.narrative}</div>
                  </div>

                  {explainPred.explanation.top_features.length > 0 && (
                    <ShapChart features={explainPred.explanation.top_features} probability={explainPred.explanation.probability} />
                  )}
                </div>
              ) : (
                <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>Run inference after training the model to see explanations.</p>
              )}
            </section>
          )}
        </div>
      </div>
    </div>
  )
}

function ShapChart({ features, probability }: {
  features: { name: string; label: string; shap_value: number; value: number }[]
  probability: number
}) {
  const maxAbs = Math.max(...features.map(f => Math.abs(f.shap_value)), 0.001)
  const ROW_H = 32
  const PAD_L = 180
  const BAR_W = 300
  const PAD_R = 80
  const W = PAD_L + BAR_W + PAD_R
  const H = features.length * ROW_H + 32
  const ZERO_X = PAD_L + BAR_W / 2

  return (
    <div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginBottom: 12 }}>
        SHAP Feature Contributions — Acceptance Probability: <strong style={{ color: probability >= 0.7 ? 'var(--status-green)' : probability >= 0.5 ? 'var(--status-orange)' : 'var(--status-red)' }}>{(probability * 100).toFixed(0)}%</strong>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
        <line x1={ZERO_X} y1={0} x2={ZERO_X} y2={H - 24} stroke="rgba(0,51,102,0.15)" strokeWidth={1} />
        {features.map((f, i) => {
          const y     = i * ROW_H + ROW_H / 2
          const bw    = (Math.abs(f.shap_value) / maxAbs) * (BAR_W / 2)
          const color = f.shap_value >= 0 ? '#27b97c' : '#e03448'
          const barX  = f.shap_value >= 0 ? ZERO_X : ZERO_X - bw
          return (
            <g key={f.name}>
              <text x={PAD_L - 8} y={y + 4} fontSize={10} fill="#6b7280" textAnchor="end" fontFamily="'Plus Jakarta Sans',sans-serif">
                {f.label.length > 22 ? f.label.slice(0, 21) + '…' : f.label}
              </text>
              <rect x={PAD_L} y={y - 10} width={BAR_W} height={20} fill="rgba(0,51,102,0.04)" rx={3} />
              <rect x={barX} y={y - 10} width={Math.max(3, bw)} height={20} fill={color} rx={3} opacity={0.82} />
              <text x={PAD_L + BAR_W + 6} y={y + 4} fontSize={9} fill={color} fontFamily="'Plus Jakarta Sans',sans-serif" fontWeight="600">
                {f.shap_value >= 0 ? '+' : ''}{f.shap_value.toFixed(3)}
              </text>
            </g>
          )
        })}
        <text x={PAD_L} y={H - 6} fontSize={8} fill="#9ca3af" textAnchor="middle">Negative</text>
        <text x={PAD_L + BAR_W} y={H - 6} fontSize={8} fill="#9ca3af" textAnchor="middle">Positive</text>
      </svg>
    </div>
  )
}
