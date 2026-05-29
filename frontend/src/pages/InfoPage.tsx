import { useState } from 'react'
import Eyebrow from '../components/Eyebrow'

type View = 'Business' | 'Engineering'

// ── Design palette (raw hex — SVG attributes cannot use CSS var()) ────────────
const C = {
  navy:    '#003366',
  navy80:  '#1a4d80',
  navy60:  '#336699',
  navy30:  '#99bbdd',
  navy10:  '#e0eaf4',
  navyTint:'rgba(0,51,102,0.05)',
  gold:    '#c8982a',
  goldTint:'rgba(200,152,42,0.08)',
  dark:    '#1c1c2e',
  mid:     '#6b7280',
  light:   '#9ca3af',
  green:   '#27b97c',
  orange:  '#f07020',
  red:     '#e03448',
}

// ── Shared styles ─────────────────────────────────────────────────────────────

const hero: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  backgroundImage: `linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)`,
  backgroundSize: '48px 48px',
  padding: '52px 48px 0',
}
const wrap: React.CSSProperties = { maxWidth: 'var(--max-width-dashboard)', margin: '0 auto' }
const card: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  borderRadius:    'var(--radius-md)',
  boxShadow:       'var(--shadow-card)',
  border:          '1px solid var(--primary-10)',
}
const bodyWrap: React.CSSProperties = {
  maxWidth:      'var(--max-width-dashboard)',
  margin:        '0 auto',
  padding:       '44px 48px',
  display:       'flex',
  flexDirection: 'column',
  gap:           40,
}

// ── Diagram 1: Agent Workflow (Business View) ─────────────────────────────────

function AgentWorkflowDiagram() {
  // U-shaped 8-step flow: 4 steps top row (→), 4 steps bottom row (←)
  const W = 900, H = 310
  const R = 24          // circle radius
  const TOP_Y = 70, BOT_Y = 220
  // Step centres — top row L→R, bottom row R→L (creates U)
  const steps = [
    { cx: 75,  cy: TOP_Y, n: '1', label: 'Daily Data Fetch',    sub: 'GA · Ads · CRM · Email' },
    { cx: 275, cy: TOP_Y, n: '2', label: 'Rules Engine',         sub: '7 business rules applied' },
    { cx: 475, cy: TOP_Y, n: '3', label: 'ML Scoring',           sub: 'Blended rule + model score' },
    { cx: 675, cy: TOP_Y, n: '4', label: 'LLM Proposal',         sub: 'Personalized email draft' },
    { cx: 675, cy: BOT_Y, n: '5', label: 'Human Approval',       sub: 'Approve · Edit · Reject' },
    { cx: 475, cy: BOT_Y, n: '6', label: 'Email Send',           sub: 'SendGrid · BCC manager' },
    { cx: 275, cy: BOT_Y, n: '7', label: 'Client Reply',         sub: 'Accept · Decline · Negotiate' },
    { cx: 75,  cy: BOT_Y, n: '8', label: 'Feedback Loop',        sub: 'Updates model confidence' },
  ]

  const stepColor = (n: string) => {
    if (['1','2','3'].includes(n)) return C.navy60
    if (n === '4') return C.gold
    if (n === '5') return C.navy80
    if (['6','7'].includes(n)) return C.navy
    return C.green
  }

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block', maxHeight: 340 }}>
      <defs>
        <marker id="arrow-gold" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill={C.gold} />
        </marker>
        <marker id="arrow-green" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill={C.green} />
        </marker>
      </defs>

      {/* Top row horizontal arrows (→) */}
      {[0,1,2].map(i => (
        <line key={`tr${i}`}
          x1={steps[i].cx + R + 2} y1={TOP_Y}
          x2={steps[i+1].cx - R - 2} y2={TOP_Y}
          stroke={C.gold} strokeWidth={1.5} markerEnd="url(#arrow-gold)" />
      ))}

      {/* Right-side down arrow */}
      <line x1={675} y1={TOP_Y + R + 2} x2={675} y2={BOT_Y - R - 2}
            stroke={C.gold} strokeWidth={1.5} markerEnd="url(#arrow-gold)" />

      {/* Bottom row horizontal arrows (←) */}
      {[4,5,6].map(i => (
        <line key={`br${i}`}
          x1={steps[i].cx - R - 2} y1={BOT_Y}
          x2={steps[i+1].cx + R + 2} y2={BOT_Y}
          stroke={C.gold} strokeWidth={1.5} markerEnd="url(#arrow-gold)" />
      ))}

      {/* Left-side feedback return arrow (up + dashed) */}
      <line x1={75} y1={BOT_Y - R - 2} x2={75} y2={TOP_Y + R + 2}
            stroke={C.green} strokeWidth={1.5} strokeDasharray="5 3" markerEnd="url(#arrow-green)" />
      <text x={30} y={(TOP_Y + BOT_Y) / 2 + 4} fontSize={8} fill={C.green}
            textAnchor="middle" fontFamily="'Plus Jakarta Sans',sans-serif"
            transform={`rotate(-90 30 ${(TOP_Y + BOT_Y) / 2})`}>
        next cycle
      </text>

      {/* Step circles and labels */}
      {steps.map(s => (
        <g key={s.n}>
          <circle cx={s.cx} cy={s.cy} r={R} fill={stepColor(s.n)} opacity={0.9} />
          <text x={s.cx} y={s.cy + 5} textAnchor="middle" fontSize={12} fontWeight="700"
                fill="#fff" fontFamily="'Plus Jakarta Sans',sans-serif">
            {s.n}
          </text>
          <text x={s.cx} y={s.cy + R + 16} textAnchor="middle" fontSize={10.5} fontWeight="600"
                fill={C.dark} fontFamily="'Plus Jakarta Sans',sans-serif">
            {s.label}
          </text>
          <text x={s.cx} y={s.cy + R + 30} textAnchor="middle" fontSize={8.5}
                fill={C.mid} fontFamily="'Plus Jakarta Sans',sans-serif">
            {s.sub}
          </text>
        </g>
      ))}
    </svg>
  )
}

// ── Diagram 2: System Architecture (Engineering View) ─────────────────────────

function ArchitectureDiagram() {
  const W = 900, H = 360

  // Layer definitions
  const layers = [
    { label: 'Browser', y: 10,  h: 70,  fill: C.navyTint, stroke: C.navy30 },
    { label: 'Backend', y: 120, h: 110, fill: C.goldTint, stroke: C.gold   },
    { label: 'Storage', y: 270, h: 70,  fill: C.navyTint, stroke: C.navy30 },
  ]

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
      <defs>
        <marker id="arch-arrow" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
          <polygon points="0 0, 7 2.5, 0 5" fill={C.navy60} />
        </marker>
        <marker id="arch-arrow-dash" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
          <polygon points="0 0, 7 2.5, 0 5" fill={C.navy30} />
        </marker>
      </defs>

      {/* Layer backgrounds */}
      {layers.map(l => (
        <rect key={l.label} x={10} y={l.y} width={630} height={l.h}
              rx={8} fill={l.fill} stroke={l.stroke} strokeWidth={1} />
      ))}

      {/* Layer labels on left edge */}
      {layers.map(l => (
        <text key={l.label + '-lbl'} x={22} y={l.y + 18} fontSize={8} fontWeight="700"
              fill={C.mid} fontFamily="'Plus Jakarta Sans',sans-serif">
          {l.label.toUpperCase()}
        </text>
      ))}

      {/* Browser layer: React + Vite box */}
      <rect x={200} y={22} width={240} height={46} rx={6}
            fill="white" stroke={C.navy60} strokeWidth={1.5} />
      <text x={320} y={41} textAnchor="middle" fontSize={12} fontWeight="700"
            fill={C.navy} fontFamily="'Plus Jakarta Sans',sans-serif">
        React 18 + TypeScript
      </text>
      <text x={320} y={57} textAnchor="middle" fontSize={9} fill={C.mid}
            fontFamily="'Plus Jakarta Sans',sans-serif">
        Vite 5 · Zustand · Inline styles · Port 5173
      </text>

      {/* HTTP arrow down Browser→Backend */}
      <line x1={320} y1={82} x2={320} y2={118} stroke={C.navy60} strokeWidth={1.5} markerEnd="url(#arch-arrow)" />
      <line x1={320} y1={118} x2={320} y2={84} stroke={C.navy30} strokeWidth={1} strokeDasharray="3 2" markerEnd="url(#arch-arrow-dash)" />
      <text x={335} y={103} fontSize={8} fill={C.mid} fontFamily="'Plus Jakarta Sans',sans-serif">HTTP /api/*</text>

      {/* Backend layer: FastAPI box */}
      <rect x={110} y={132} width={420} height={86} rx={6}
            fill="white" stroke={C.gold} strokeWidth={1.5} />
      <text x={320} y={152} textAnchor="middle" fontSize={12} fontWeight="700"
            fill={C.navy} fontFamily="'Plus Jakarta Sans',sans-serif">
        FastAPI · uvicorn · Port 8000
      </text>
      <text x={320} y={168} textAnchor="middle" fontSize={9} fill={C.mid}
            fontFamily="'Plus Jakarta Sans',sans-serif">
        backend/routers/ → src/agents/ · src/ml/ · src/nlp/ · src/data_sources/
      </text>
      {/* Router pills */}
      {['opportunities','proposals','pilot','ml','text-signals','negotiations','alerts','clients'].map((r, i) => {
        const cols = 4, col = i % cols, row = Math.floor(i / cols)
        const x = 125 + col * 100, y = 182 + row * 18
        return (
          <g key={r}>
            <rect x={x} y={y} width={88} height={13} rx={3} fill={C.navyTint} stroke={C.navy30} strokeWidth={0.5} />
            <text x={x + 44} y={y + 9.5} textAnchor="middle" fontSize={7.5} fill={C.navy60}
                  fontFamily="'Plus Jakarta Sans',sans-serif">/api/{r}</text>
          </g>
        )
      })}

      {/* Backend→Storage arrow */}
      <line x1={320} y1={232} x2={320} y2={268} stroke={C.navy60} strokeWidth={1.5} markerEnd="url(#arch-arrow)" />
      <line x1={320} y1={268} x2={320} y2={234} stroke={C.navy30} strokeWidth={1} strokeDasharray="3 2" markerEnd="url(#arch-arrow-dash)" />

      {/* Storage layer: SQLite */}
      <rect x={80} y={282} width={280} height={46} rx={6}
            fill="white" stroke={C.navy60} strokeWidth={1.5} />
      <text x={220} y={302} textAnchor="middle" fontSize={11} fontWeight="700"
            fill={C.navy} fontFamily="'Plus Jakarta Sans',sans-serif">
        SQLite — data/db/opportunities.db
      </text>
      <text x={220} y={318} textAnchor="middle" fontSize={8} fill={C.mid}
            fontFamily="'Plus Jakarta Sans',sans-serif">
        clients · metrics · opportunities · proposals · feedback
      </text>

      {/* Right column: External APIs */}
      <rect x={660} y={10} width={230} height={340} rx={8}
            fill={C.navyTint} stroke={C.navy30} strokeWidth={1} />
      <text x={775} y={28} textAnchor="middle" fontSize={8} fontWeight="700" letterSpacing="1.5"
            fill={C.mid} fontFamily="'Plus Jakarta Sans',sans-serif">EXTERNAL APIS (PROD)</text>

      {[
        { label: 'Google Analytics',  note: 'CTR · bounce · conversions' },
        { label: 'Meta Ads Manager',  note: 'CTR · ROAS · ad spend' },
        { label: 'HubSpot CRM',       note: 'days inactive · contacts' },
        { label: 'Mailchimp',         note: 'open rate · click rate' },
        { label: 'SendGrid',          note: 'email delivery · BCC' },
        { label: 'Anthropic / OpenAI',note: 'proposal generation · NLP' },
        { label: 'Stripe',            note: 'payment link creation' },
        { label: 'Slack',             note: 'alert webhooks' },
      ].map((api, i) => (
        <g key={api.label}>
          <rect x={670} y={38 + i * 38} width={210} height={30} rx={5}
                fill="white" stroke={C.navy30} strokeWidth={0.8} />
          <text x={685} y={56 + i * 38} fontSize={9} fontWeight="600" fill={C.navy}
                fontFamily="'Plus Jakarta Sans',sans-serif">{api.label}</text>
          <text x={685} y={67 + i * 38} fontSize={7.5} fill={C.mid}
                fontFamily="'Plus Jakarta Sans',sans-serif">{api.note}</text>
        </g>
      ))}

      {/* Dashed line connecting backend to External APIs panel */}
      <line x1={640} y1={175} x2={658} y2={175} stroke={C.navy30}
            strokeWidth={1} strokeDasharray="4 3" markerEnd="url(#arch-arrow-dash)" />
    </svg>
  )
}

// ── Diagram 3: Detection Pipeline (Engineering View) ──────────────────────────

function DetectionPipelineDiagram() {
  const W = 860, H = 140
  const boxes = [
    { label: 'Client List',      sub: 'get_all_clients()', color: C.navy30 },
    { label: 'Metrics Fetch',    sub: 'GA · Ads · Email · SEO · CRM', color: C.navy60 },
    { label: 'Rules Engine',     sub: 'evaluate(metrics)', color: C.navy80 },
    { label: 'ML Probability',   sub: 'predict_proba() + SHAP', color: C.navy },
    { label: 'Ranked Results',   sub: 'blended_score desc', color: C.gold },
  ]
  const BW = 142, BH = 64, GAP = 30
  const totalW = boxes.length * BW + (boxes.length - 1) * GAP
  const startX = (W - totalW) / 2

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
      <defs>
        <marker id="pipe-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill={C.gold} />
        </marker>
      </defs>

      {boxes.map((b, i) => {
        const x = startX + i * (BW + GAP)
        const midY = H / 2
        const nextX = x + BW
        return (
          <g key={b.label}>
            <rect x={x} y={midY - BH / 2} width={BW} height={BH} rx={6}
                  fill={b.color} opacity={0.9} />
            <text x={x + BW / 2} y={midY - 7} textAnchor="middle" fontSize={10} fontWeight="700"
                  fill="#fff" fontFamily="'Plus Jakarta Sans',sans-serif">{b.label}</text>
            <text x={x + BW / 2} y={midY + 10} textAnchor="middle" fontSize={7.5}
                  fill="rgba(255,255,255,0.7)" fontFamily="'Plus Jakarta Sans',sans-serif">{b.sub}</text>

            {/* Arrow to next box */}
            {i < boxes.length - 1 && (
              <line x1={nextX + 2} y1={midY} x2={nextX + GAP - 2} y2={midY}
                    stroke={C.gold} strokeWidth={1.5} markerEnd="url(#pipe-arrow)" />
            )}
          </g>
        )
      })}

      {/* Fallback note */}
      <text x={W / 2} y={H - 8} textAnchor="middle" fontSize={8} fill={C.mid}
            fontFamily="'Plus Jakarta Sans',sans-serif">
        ML step is skipped when no model is trained — rule score is used directly
      </text>
    </svg>
  )
}

// ── Diagram 4: NLP Pipeline (Engineering View) ────────────────────────────────

function NlpPipelineDiagram() {
  const W = 860, H = 120
  const boxes = [
    { label: 'Raw Text',         sub: 'Email · Call · CRM note',   color: C.navy30 },
    { label: 'Keyword Match',    sub: 'Pattern matching pass',      color: C.navy60 },
    { label: 'LLM Extraction',   sub: 'Structured JSON (claude-haiku)', color: C.navy80 },
    { label: 'Signal Flags',     sub: 'churn · price · urgency',   color: C.navy },
    { label: 'ML Features',      sub: '+5 features → model',       color: C.gold },
  ]
  const BW = 142, BH = 58, GAP = 30
  const totalW = boxes.length * BW + (boxes.length - 1) * GAP
  const startX = (W - totalW) / 2
  const midY = H / 2

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
      <defs>
        <marker id="nlp-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill={C.gold} />
        </marker>
      </defs>
      {boxes.map((b, i) => {
        const x = startX + i * (BW + GAP)
        return (
          <g key={b.label}>
            <rect x={x} y={midY - BH / 2} width={BW} height={BH} rx={6} fill={b.color} opacity={0.9} />
            <text x={x + BW / 2} y={midY - 6} textAnchor="middle" fontSize={10} fontWeight="700"
                  fill="#fff" fontFamily="'Plus Jakarta Sans',sans-serif">{b.label}</text>
            <text x={x + BW / 2} y={midY + 9} textAnchor="middle" fontSize={7.5}
                  fill="rgba(255,255,255,0.7)" fontFamily="'Plus Jakarta Sans',sans-serif">{b.sub}</text>
            {i < boxes.length - 1 && (
              <line x1={x + BW + 2} y1={midY} x2={x + BW + GAP - 2} y2={midY}
                    stroke={C.gold} strokeWidth={1.5} markerEnd="url(#nlp-arrow)" />
            )}
          </g>
        )
      })}
    </svg>
  )
}

// ── Business View ─────────────────────────────────────────────────────────────

function BusinessView() {
  const opps = [
    { type: 'Landing Page Optimization', signals: 'High bounce rate (>60%) + low conversion rate (<1.5%)', price: '$350' },
    { type: 'SEO Content Package',       signals: 'Low organic traffic + declining keyword rankings',         price: '$500' },
    { type: 'Retargeting Campaign',      signals: 'High CTR but low conversion + no active retargeting',     price: '$400' },
    { type: 'Email Automation',          signals: 'Low email open rate (<15%) + high pages/session',         price: '$300' },
    { type: 'Express Reactivation',      signals: 'Client inactive in CRM for 90+ days',                     price: '$150' },
    { type: 'Conversion Rate Audit',     signals: 'Ad spend >$1,000/mo with ROAS <2×',                       price: '$250' },
    { type: 'Ad Budget Expansion',       signals: 'ROAS >4× + CTR >3% (ads are performing, budget is limiting)', price: '$400' },
  ]

  const painPoints = [
    {
      title: 'Scale vs. attention',
      body: 'An account manager handling 20 clients cannot review every metric dashboard every day. Opportunities identified manually tend to be the obvious ones; subtle cross-channel patterns go unseen.',
    },
    {
      title: 'Timing',
      body: 'A spike in bounce rate is most actionable in the week it appears. By the time it surfaces in a monthly report, the client may have paused their campaign or found another agency.',
    },
    {
      title: 'Proposal quality at volume',
      body: 'Writing a personalized proposal for each detected opportunity takes 20–40 minutes per client. At scale, account managers triage by gut feel rather than data, and many actionable accounts never receive outreach.',
    },
    {
      title: 'Outcome tracking',
      body: 'Without systematic recording of which proposals were accepted, rejected, or ignored, the agency has no feedback loop. The same outreach strategy is repeated regardless of what has actually worked.',
    },
  ]

  const tiers = [
    {
      tier: 'A',
      label: 'Full Human Control',
      condition: 'Any proposal',
      action: 'Agent generates a draft and saves it. No email is sent without explicit human sign-off via the Proposals UI.',
      color: C.mid,
    },
    {
      tier: 'B',
      label: 'Human Approval Required',
      condition: 'Score 70–89 OR suggested price > $200',
      action: 'Agent notifies the account manager via Slack. Manager clicks Approve or Reject before any email is dispatched.',
      color: C.gold,
    },
    {
      tier: 'C',
      label: 'Autonomous Send',
      condition: 'Score ≥ 90 AND price ≤ $200 AND repeat buyer',
      action: 'Agent sends the email directly, BCC-ing the account manager. A 30-minute cancellation window is logged.',
      color: C.green,
    },
  ]

  const th: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', padding: '11px 16px', color: '#fff', background: 'var(--primary)', textAlign: 'left', whiteSpace: 'nowrap' }
  const td: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 16px', color: 'var(--dark)', verticalAlign: 'top' }

  return (
    <div style={bodyWrap}>

      {/* Problem statement */}
      <section>
        <Eyebrow>The Problem</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
          Revenue left on the table at <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>scale</em>
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {painPoints.map(p => (
            <div key={p.title} style={{ ...card, padding: 24, borderLeft: '3px solid var(--gold)' }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: 'var(--dark)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '1px' }}>
                {p.title}
              </div>
              <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', lineHeight: 1.75, margin: 0 }}>
                {p.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Agent loop diagram */}
      <section>
        <Eyebrow>How It Works</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 8px' }}>
          The complete agent <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>loop</em>
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', lineHeight: 1.7, marginBottom: 24, maxWidth: 720 }}>
          Every 24 hours the agent fetches the latest data for every client, evaluates all 7 opportunity rules, scores and ranks detected opportunities, generates proposal drafts via LLM, and routes them through a human-supervised dispatch workflow. Client replies are recorded and used to refine future detection.
        </p>
        <div style={{ ...card, padding: 32 }}>
          <AgentWorkflowDiagram />
        </div>
      </section>

      {/* The 7 opportunity types */}
      <section>
        <Eyebrow>Detection Rules</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 8px' }}>
          7 opportunity <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>types</em>
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', lineHeight: 1.7, marginBottom: 20, maxWidth: 700 }}>
          Each rule was derived from agency historical data and reflects a specific cross-channel signal combination. A client can trigger multiple rules in the same scan; all are ranked independently by score.
        </p>
        <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', border: '1px solid var(--primary-10)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={th}>Opportunity Type</th>
                <th style={th}>Signal Conditions</th>
                <th style={{ ...th, textAlign: 'right' }}>Suggested Price</th>
              </tr>
            </thead>
            <tbody>
              {opps.map((o, i) => (
                <tr key={o.type} style={{ background: i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)', borderBottom: '1px solid var(--primary-10)' }}>
                  <td style={{ ...td, fontWeight: 600 }}>{o.type}</td>
                  <td style={{ ...td, color: 'var(--mid)' }}>{o.signals}</td>
                  <td style={{ ...td, textAlign: 'right', fontFamily: 'var(--fd)', fontSize: 16, fontWeight: 300, color: 'var(--gold)' }}>{o.price}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Autonomy tiers */}
      <section>
        <Eyebrow>Autonomy Model</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 8px' }}>
          Three tiers of <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>autonomy</em>
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', lineHeight: 1.7, marginBottom: 20, maxWidth: 700 }}>
          The tier is computed per opportunity at dispatch time using score, suggested price, and client history. All proposals start at Tier A; Tier C requires explicit configuration and a trained ML model.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {tiers.map(t => (
            <div key={t.tier} style={{ ...card, padding: 24, display: 'flex', alignItems: 'stretch', gap: 20 }}>
              <div style={{ width: 48, height: 48, borderRadius: '50%', background: t.color, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, alignSelf: 'flex-start', marginTop: 2 }}>
                <span style={{ fontFamily: 'var(--fd)', fontSize: 18, fontWeight: 300, color: '#fff' }}>{t.tier}</span>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6, flexWrap: 'wrap' }}>
                  <span style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 700, color: 'var(--dark)' }}>{t.label}</span>
                  <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: t.color, background: `${t.color}18`, padding: '2px 10px', borderRadius: 'var(--radius-pill)', fontWeight: 600 }}>{t.condition}</span>
                </div>
                <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', lineHeight: 1.7, margin: 0 }}>{t.action}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Data sources */}
      <section>
        <Eyebrow>Data Sources</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
          What the agent <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>reads</em>
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {[
            { name: 'Google Analytics', metrics: ['Bounce rate', 'Pages/session', 'Conversion rate', 'Organic traffic'], note: 'GA4 Data API v1' },
            { name: 'Meta Ads Manager', metrics: ['CTR', 'CPC', 'ROAS', 'Ad spend (daily)'], note: 'Marketing API v18' },
            { name: 'HubSpot CRM',      metrics: ['Days since last contact', 'Days inactive', 'Deal stage'], note: 'CRM API v3' },
            { name: 'Mailchimp',        metrics: ['Email open rate', 'Click-through rate', 'List health'], note: 'Marketing API v3' },
            { name: 'Semrush / SEO',    metrics: ['Organic traffic', 'Keyword rankings', 'Visibility score'], note: 'SEMrush API' },
            { name: 'Email / CRM Notes',metrics: ['Sentiment', 'Price mentions', 'Churn signals', 'Urgency flags'], note: 'Parsed by NLP pipeline' },
          ].map(src => (
            <div key={src.name} style={{ ...card, padding: 20 }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: 'var(--primary)', marginBottom: 4 }}>{src.name}</div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)', letterSpacing: '1px', textTransform: 'uppercase', marginBottom: 10 }}>{src.note}</div>
              <ul style={{ margin: 0, paddingLeft: 14, display: 'flex', flexDirection: 'column', gap: 3 }}>
                {src.metrics.map(m => (
                  <li key={m} style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{m}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

// ── Engineering View ──────────────────────────────────────────────────────────

function EngineeringView() {
  const stack = [
    { layer: 'Frontend',   tech: 'React 18 + TypeScript 5.6',     detail: 'Strict mode · Vite 5 dev server · Zustand global state · Inline React.CSSProperties (no CSS framework)' },
    { layer: 'Routing',    tech: 'State-based (no router library)', detail: 'Page union type in App.tsx · switch in renderPage() · nav group dropdowns in Nav.tsx' },
    { layer: 'API client', tech: 'Native fetch in api.ts',          detail: 'Single base request() fn · all HTTP calls centralised · typed interfaces per endpoint' },
    { layer: 'Backend',    tech: 'FastAPI 0.115 + Uvicorn',         detail: '9 routers, one per domain · startup hook runs init_db() + migrate_db() · CORS for :5173' },
    { layer: 'Database',   tech: 'SQLite (built-in)',               detail: 'WAL mode · 8 tables · no ORM · raw SQL via sqlite3.Row dicts · file at data/db/opportunities.db' },
    { layer: 'ML',         tech: 'scikit-learn RandomForest',       detail: '200 trees · balanced class weights · max_depth=8 · SHAP TreeExplainer · joblib persistence' },
    { layer: 'NLP',        tech: 'Keyword + LLM extraction',        detail: 'Two-pass: keyword patterns first, then claude-haiku-4-5 for structured JSON (temperature=0)' },
    { layer: 'LLM',        tech: 'Anthropic / OpenAI (switchable)', detail: 'Configured via LLM_PROVIDER env var · deterministic template fallback when no API key' },
  ]

  const modules = [
    { path: 'backend/',                  note: 'FastAPI app + 9 routers (thin wrappers over src/)' },
    { path: 'src/agents/',               note: 'scorer · rules · proposal_generator · negotiator · email_sender · feedback_loop · auto_sender · alerts · payment_link' },
    { path: 'src/data_sources/',         note: 'crm · google_analytics · meta_ads · email_marketing · seo · text_signals' },
    { path: 'src/ml/',                   note: 'model (train/load) · dataset (feature engineering) · inference (predict_for_all) · explainer (SHAP)' },
    { path: 'src/nlp/',                  note: 'pipeline (orchestrator) · signal_extractor (keyword + LLM)' },
    { path: 'src/db/',                   note: 'schema (init_db, migrate_db, get_connection)' },
    { path: 'src/synthetic/',            note: 'generator (75 synthetic clients + metrics via Faker)' },
    { path: 'scripts/',                  note: 'seed_db · daily_job · train_model · run_detection · process_text' },
    { path: 'frontend/src/pages/',       note: '8 pages: Opportunities · AlertFeed · Accuracy · Proposals · Pilot · MLModel · TextSignals · Negotiation · Info' },
    { path: 'frontend/src/components/',  note: 'Nav · Footer · Eyebrow (shared OPB components)' },
    { path: 'frontend/src/services/',    note: 'api.ts (all typed HTTP calls)' },
    { path: 'frontend/src/styles/',      note: 'tokens.css (all CSS custom properties)' },
  ]

  const dbTables = [
    { name: 'clients',          cols: 'id · name · industry · account_age_days · is_demo_scenario · account_manager' },
    { name: 'client_metrics',   cols: 'client_id · date · bounce_rate · ctr · roas · email_open_rate · organic_traffic · days_inactive · …' },
    { name: 'opportunities',    cols: 'id · client_id · opportunity_type · score · ml_probability · status · detected_at' },
    { name: 'proposals',        cols: 'id · opportunity_id · client_id · subject · body · status · approved_by · sent_at · suggested_price' },
    { name: 'negotiation_log',  cols: 'proposal_id · turn · role · message · intent · offer_price · timestamp' },
    { name: 'feedback_log',     cols: 'proposal_id · client_id · intent · outcome · confidence_delta · revenue · simulated' },
    { name: 'text_signals',     cols: 'client_id · source · raw_text · sentiment · mentions_price · churn_risk · urgency_signal · processed_at' },
    { name: 'alerts',           cols: 'client_id · opportunity_type · score · label · suggested_price · timestamp · slack_payload' },
  ]

  const th: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', padding: '10px 16px', color: '#fff', background: 'var(--primary)', textAlign: 'left', whiteSpace: 'nowrap' }
  const td: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 12, padding: '9px 16px', color: 'var(--dark)', verticalAlign: 'top' }
  const code: React.CSSProperties = { fontFamily: 'Courier New, monospace', fontSize: 11, background: 'var(--primary-10)', color: 'var(--primary)', padding: '1px 6px', borderRadius: 4 }

  return (
    <div style={bodyWrap}>

      {/* Tech stack */}
      <section>
        <Eyebrow>Technology Stack</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
          Layers and <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>dependencies</em>
        </h2>
        <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', border: '1px solid var(--primary-10)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ ...th, width: 120 }}>Layer</th>
                <th style={th}>Technology</th>
                <th style={th}>Notes</th>
              </tr>
            </thead>
            <tbody>
              {stack.map((s, i) => (
                <tr key={s.layer} style={{ background: i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)', borderBottom: '1px solid var(--primary-10)' }}>
                  <td style={{ ...td, fontWeight: 700, color: 'var(--primary)', whiteSpace: 'nowrap' }}>{s.layer}</td>
                  <td style={{ ...td, fontWeight: 600, whiteSpace: 'nowrap' }}>{s.tech}</td>
                  <td style={{ ...td, color: 'var(--mid)' }}>{s.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Architecture diagram */}
      <section>
        <Eyebrow>System Architecture</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 8px' }}>
          Component <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>layout</em>
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', lineHeight: 1.7, marginBottom: 24, maxWidth: 720 }}>
          The browser communicates exclusively with FastAPI over HTTP. FastAPI routers are thin adapters that delegate to <span style={code}>src/</span> modules. In demo mode all external API calls are intercepted and return synthetic data from SQLite. In production each data source module calls the real API.
        </p>
        <div style={{ ...card, padding: 32 }}>
          <ArchitectureDiagram />
        </div>
      </section>

      {/* Detection pipeline */}
      <section>
        <Eyebrow>Detection Pipeline</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 8px' }}>
          From client list to ranked <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>opportunities</em>
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', lineHeight: 1.7, marginBottom: 24, maxWidth: 720 }}>
          <span style={code}>score_all_clients()</span> orchestrates the full pipeline. Each client's metrics are merged into a single flat dict, evaluated against all 7 rules, and optionally augmented with an ML probability. The blended score — 0.55 × ML probability × 100 + 0.45 × rule score — drives the final ranking.
        </p>
        <div style={{ ...card, padding: 32 }}>
          <DetectionPipelineDiagram />
        </div>
      </section>

      {/* NLP pipeline */}
      <section>
        <Eyebrow>NLP Pipeline</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 8px' }}>
          Unstructured text to ML <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>features</em>
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', lineHeight: 1.7, marginBottom: 24, maxWidth: 720 }}>
          Client emails, call transcripts, and CRM notes are processed in two passes. A fast keyword scan runs first; if it produces ambiguous results, a second pass calls the LLM with a structured JSON output prompt at <span style={code}>temperature=0</span>. If the LLM call exceeds 3 seconds or fails, the keyword result is used as fallback. Five signal flags are written back to <span style={code}>text_signals</span> and injected as additional ML features.
        </p>
        <div style={{ ...card, padding: 32 }}>
          <NlpPipelineDiagram />
        </div>
      </section>

      {/* Module structure */}
      <section>
        <Eyebrow>Module Structure</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
          Directory <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>map</em>
        </h2>
        <div style={{ ...card, padding: 28 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {modules.map(m => (
              <div key={m.path} style={{ display: 'flex', gap: 16, alignItems: 'flex-start', padding: '8px 0', borderBottom: '1px solid var(--primary-10)' }}>
                <code style={{ ...code, fontSize: 12, whiteSpace: 'nowrap', flexShrink: 0, marginTop: 1 }}>{m.path}</code>
                <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', lineHeight: 1.6 }}>{m.note}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Data schema */}
      <section>
        <Eyebrow>Data Schema</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 8px' }}>
          SQLite <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>tables</em>
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', lineHeight: 1.7, marginBottom: 20 }}>
          Schema is initialised at startup via <span style={code}>init_db()</span> and migrated via <span style={code}>migrate_db()</span> in <span style={code}>src/db/schema.py</span>. All connections use <span style={code}>sqlite3.Row</span> for dict-style access and WAL journal mode for concurrent reads.
        </p>
        <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', border: '1px solid var(--primary-10)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ ...th, width: 180 }}>Table</th>
                <th style={th}>Key Columns</th>
              </tr>
            </thead>
            <tbody>
              {dbTables.map((t, i) => (
                <tr key={t.name} style={{ background: i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)', borderBottom: '1px solid var(--primary-10)' }}>
                  <td style={{ ...td, fontWeight: 700, fontFamily: 'Courier New, monospace', fontSize: 12, color: 'var(--primary)' }}>{t.name}</td>
                  <td style={{ ...td, color: 'var(--mid)', fontFamily: 'Courier New, monospace', fontSize: 11 }}>{t.cols}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Key engineering decisions */}
      <section>
        <Eyebrow>Design Decisions</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 20px' }}>
          Why these <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>choices</em>
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {[
            { decision: 'SQLite over PostgreSQL',     rationale: 'The workload is read-heavy with one writer (the daily job). SQLite with WAL mode handles this without the operational overhead of a containerised database. Migration to PostgreSQL requires only swapping the connection string in schema.py.' },
            { decision: 'No ORM',                     rationale: 'The schema is stable and queries are straightforward. Raw SQL with sqlite3.Row gives full control over query plans and avoids the impedance mismatch that ORMs introduce when joining across the opportunity and proposal tables.' },
            { decision: 'Inline styles over CSS classes', rationale: 'The OPB design system requires exact values (rgba(201,168,76,0.12) for active nav backgrounds) that have no utility-class equivalent. Inline React.CSSProperties also provides TypeScript coverage on every property name.' },
            { decision: 'Hand-coded SVG over charting libraries', rationale: 'Recharts and Plotly ship their own visual vocabulary. Every pixel of every chart in this system needs to follow OPB colour rules — categorical series use only the navy gradient, status colours are reserved for data signals only. A library cannot enforce these constraints.' },
            { decision: 'Rule engine + ML blend',     rationale: 'Rules are explainable and immediately useful even before any training data exists. The ML model improves ranking precision once enough feedback has been collected. The 0.55/0.45 blend lets the model take increasing influence without fully deprecating the rules.' },
            { decision: 'Demo mode via synthetic data', rationale: 'All data sources (GA, Meta Ads, HubSpot, Mailchimp) are proxied through demo adapters that return deterministic synthetic data seeded with Faker. This makes the full stack runnable without any real API credentials, useful for internal demos and development.' },
          ].map(d => (
            <div key={d.decision} style={{ ...card, padding: 24 }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: 'var(--dark)', marginBottom: 8 }}>{d.decision}</div>
              <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', lineHeight: 1.75, margin: 0 }}>{d.rationale}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function InfoPage() {
  const [view, setView] = useState<View>('Business')

  const tabBtn = (v: View): React.CSSProperties => ({
    background: 'none', border: 'none', cursor: 'pointer',
    fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 500,
    letterSpacing: '1.5px', textTransform: 'uppercase',
    padding: '10px 24px', marginBottom: -1,
    borderBottom: `2px solid ${view === v ? 'var(--gold-light)' : 'transparent'}`,
    color: view === v ? 'var(--gold-light)' : 'rgba(255,255,255,0.4)',
    transition: 'color 0.15s',
  })

  return (
    <div>
      {/* ── Hero with tab bar ── */}
      <div style={hero}>
        <div style={wrap}>
          <Eyebrow light>System Overview</Eyebrow>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: '#fff', margin: '0 0 6px', lineHeight: 1.2 }}>
            Hidden Opportunities <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Agent</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'rgba(255,255,255,0.45)', marginBottom: 40, maxWidth: 640 }}>
            An autonomous agent that detects upsell and cross-sell opportunities in marketing agency client data, generates personalized proposals, and manages the full detect → propose → approve → send → feedback cycle.
          </p>

          <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
            <button style={tabBtn('Business')}    onClick={() => setView('Business')}>Business View</button>
            <button style={tabBtn('Engineering')} onClick={() => setView('Engineering')}>Engineering View</button>
          </div>
        </div>
      </div>

      {/* ── Body ── */}
      <div style={{ backgroundColor: 'var(--light)' }}>
        {view === 'Business' ? <BusinessView /> : <EngineeringView />}
      </div>
    </div>
  )
}
