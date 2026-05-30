const BASE = '/api'

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...opts?.headers },
  })
  if (!res.ok) throw new Error(`${res.status} ${path}`)
  return res.json() as Promise<T>
}

// ── Type definitions ────────────────────────────────────────────────────────

export interface Opportunity {
  client_id: string
  client_name: string
  industry: string
  opportunity_type: string
  label: string
  score: number
  ml_probability: number | null
  blended_score: number
  suggested_price: number
  rationale: string
  triggered_signals: string[]
  is_demo_scenario: number
}

export interface Alert {
  score: number
  label: string
  client_name: string
  suggested_price: number
  timestamp: string
  opportunity_type: string
  slack_payload?: Record<string, unknown>
}

export interface AccuracyRow {
  client: string
  expected: string
  detected: string
  tp: number; fp: number; fn: number
  status: 'Perfect' | 'Extra' | 'Missed'
}

export interface AccuracyMetrics {
  precision: number; recall: number; f1: number
  tp: number; fp: number; fn: number
}

export interface Proposal {
  id: string
  client_id: string
  client_name: string
  industry: string
  opportunity_type: string
  label: string
  score: number | null
  suggested_price: number
  status: string
  created_at: string
  subject: string
  body: string
  is_demo_scenario: number
  approved_by?: string
  sent_at?: string
  updated_at?: string
}

export interface PilotMetrics {
  total_opportunities: number
  proposals_generated: number
  proposals_sent: number
  autonomous_sent: number
  approved_sent: number
  proposals_accepted: number
  acceptance_rate_pct: number
  total_revenue: number
  escalations: number
  proposals_rejected: number
  time_saved_hours: number
  by_type: { opportunity_type: string; cnt: number; accepted: number }[]
}

export interface MLStatus {
  is_trained: boolean
  metadata: {
    trained_at: string
    n_samples: number
    n_features: number
    cv_folds: number
    metrics: { auc_roc: number; avg_precision: number; precision: number; recall: number; f1: number }
  } | null
}

export interface MLPrediction {
  client_id: string
  client_name: string
  industry: string
  opportunity_type: string
  rule_score: number
  ml_probability: number | null
  blended_score: number
  suggested_price: number
  is_demo_scenario: number
  explanation: {
    probability: number
    narrative: string
    shap_available: boolean
    top_features: { name: string; label: string; shap_value: number; value: number }[]
  } | null
}

export interface TextSummary {
  total_signals: number
  processed: number
  unprocessed: number
  churn_count: number
  urgency_count: number
  counts_by_type: Record<string, number>
}

export interface SignalEntry {
  raw_text: string
  source: string
  sentiment: number | null
  mentions_price: boolean
  asks_for_results: boolean
  churn_risk: boolean
  urgency_signal: boolean
  interest_signal: boolean
  processed_at: string
}

export interface NegotiationSummary {
  total_negotiations: number
  active: number
  accepted: number
  rejected: number
  escalated: number
  auto_resolution_rate: number
}

export interface NegotiationTurn {
  role: string
  message: string
  intent: string | null
  offer_price: number | null
  timestamp: string
}

export interface Client {
  id: string
  name: string
  industry: string
  is_demo_scenario?: number
}

export interface ClientDetail {
  client: {
    id: string; name: string; industry: string; company_size: string
    account_age_days: number; monthly_spend: number; contact_email: string
    account_manager: string; is_demo_scenario: number
    propensity_tier: string | null; preferred_channel: string
  }
  metrics: {
    bounce_rate?: number; pages_per_session?: number; conversion_rate?: number
    organic_traffic?: number; ctr?: number; cpc?: number; roas?: number
    ad_spend?: number; email_open_rate?: number; email_click_rate?: number
    keyword_rankings?: number; days_inactive?: number; days_since_last_contact?: number
    monthly_spend?: number; account_age_days?: number
  }
  opportunities: Record<string, unknown>[]
  signals_summary: Record<string, unknown>
  signals: Record<string, unknown>[]
  proposals: { id: string; opportunity_type: string; subject: string; status: string; suggested_price: number; sent_at: string | null; payment_link: string | null }[]
  feedback: Record<string, unknown>[]
}

// ── API methods ─────────────────────────────────────────────────────────────

export const api = {
  opportunities: {
    list: (opp_type = 'All', industry = 'All', demo_only = false) =>
      request<Opportunity[]>(`/opportunities?opp_type=${encodeURIComponent(opp_type)}&industry=${encodeURIComponent(industry)}&demo_only=${demo_only}`),
    meta: () =>
      request<{ types: string[]; industries: string[] }>('/opportunities/meta'),
  },

  alerts: {
    list: () => request<Alert[]>('/alerts'),
    run: (scope: string, min_score: number) =>
      request<{ dispatched: number }>('/alerts/run', {
        method: 'POST',
        body: JSON.stringify({ scope, min_score }),
      }),
    clear: () => request<{ cleared: boolean }>('/alerts', { method: 'DELETE' }),
  },

  accuracy: {
    get: () => request<{ rows: AccuracyRow[]; metrics: AccuracyMetrics }>('/accuracy'),
  },

  proposals: {
    list: (status = 'All', opp_type = 'All', demo_only = false) =>
      request<Proposal[]>(`/proposals?status=${status}&opp_type=${encodeURIComponent(opp_type)}&demo_only=${demo_only}`),
    generateAll: (min_score: number) =>
      request<{ generated: number; total: number }>('/proposals/generate-all', {
        method: 'POST',
        body: JSON.stringify({ min_score }),
      }),
    approve: (id: string) =>
      request<{ approved: boolean }>(`/proposals/${id}/approve`, { method: 'POST' }),
    reject: (id: string, reason = 'Rejected via UI') =>
      request<{ rejected: boolean }>(`/proposals/${id}/reject`, {
        method: 'POST', body: JSON.stringify({ reason }),
      }),
    updateBody: (id: string, body: string) =>
      request<{ updated: boolean }>(`/proposals/${id}/body`, {
        method: 'PATCH', body: JSON.stringify({ body }),
      }),
    revoke: (id: string) =>
      request<{ revoked: boolean }>(`/proposals/${id}/revoke`, { method: 'POST' }),
    metrics: (id: string) =>
      request<Record<string, number>>(`/proposals/${id}/metrics`),
  },

  pilot: {
    detect: (client_id: string) =>
      request<{ opportunities: { label: string; opportunity_type: string; score: number; suggested_price: number; rationale: string; tier: string }[] }>('/pilot/detect', {
        method: 'POST', body: JSON.stringify({ client_id }),
      }),
    generate: (client_id: string) =>
      request<{ proposal_id: string; subject: string; status: string; already_existed: boolean }>('/pilot/generate', {
        method: 'POST', body: JSON.stringify({ client_id }),
      }),
    send: (proposal_id: string, opp_score: number, opp_price: number, opp_type: string) =>
      request<{ sent: boolean; tier: string }>('/pilot/send', {
        method: 'POST', body: JSON.stringify({ proposal_id, opp_score, opp_price, opp_type }),
      }),
    reply: (proposal_id: string, intent: string, notes = '', simulated = true) =>
      request<Record<string, unknown>>('/pilot/reply', {
        method: 'POST', body: JSON.stringify({ proposal_id, intent, notes, simulated }),
      }),
    metrics: () => request<PilotMetrics>('/pilot/metrics'),
    sentLog: () => request<Record<string, unknown>[]>('/pilot/sent-log'),
    feedbackLog: () => request<{ feedback: Record<string, unknown>[]; calendars: unknown[]; escalations: unknown[]; intent_labels: Record<string, string>; all_intents: string[] }>('/pilot/feedback-log'),
    autoQueue: () => request<Record<string, unknown>>('/pilot/auto-queue'),
    processAutoQueue: () => request<{ sent: number }>('/pilot/process-auto-queue', { method: 'POST' }),
  },

  ml: {
    status: () => request<MLStatus>('/ml/status'),
    train: () => request<Record<string, unknown>>('/ml/train', { method: 'POST' }),
    predictions: () => request<MLPrediction[]>('/ml/predictions'),
    featureImportance: () => request<{ name: string; label: string; importance: number }[]>('/ml/feature-importance'),
    summary: () => request<{ total_predictions: number; high_prob_count: number; avg_ml_probability: number | null }>('/ml/summary'),
    history: () => request<Record<string, unknown>[]>('/ml/history'),
  },

  textSignals: {
    summary: () => request<TextSummary>('/text-signals/summary'),
    client: (id: string) => request<{ signals: SignalEntry[]; summary: Record<string, unknown> }>(`/text-signals/client/${id}`),
    allSummaries: () => request<Record<string, unknown>[]>('/text-signals/all-summaries'),
    urgency: () => request<Record<string, unknown>[]>('/text-signals/urgency'),
    process: (reprocess_all = false) =>
      request<{ total_processed: number; churn_alerts: number; urgency_alerts: number }>('/text-signals/process', {
        method: 'POST', body: JSON.stringify({ reprocess_all }),
      }),
  },

  negotiations: {
    summary: () => request<NegotiationSummary>('/negotiations/summary'),
    active: () => request<Record<string, unknown>[]>('/negotiations/active'),
    history: () => request<Record<string, unknown>[]>('/negotiations/history'),
    thread: (pid: string) => request<NegotiationTurn[]>(`/negotiations/${pid}/thread`),
    reply: (pid: string, message: string, simulated = false) =>
      request<Record<string, unknown>>(`/negotiations/${pid}/reply`, {
        method: 'POST', body: JSON.stringify({ message, simulated }),
      }),
    kill: (pid: string) =>
      request<{ killed: boolean }>(`/negotiations/${pid}/kill`, {
        method: 'POST', body: JSON.stringify({ reason: 'manual_kill_switch_ui' }),
      }),
    start: (pid: string) =>
      request<Record<string, unknown>>(`/negotiations/${pid}/start`, { method: 'POST' }),
    tooExpensive: (proposal_id: string) =>
      request<Record<string, unknown>>('/negotiations/too-expensive', {
        method: 'POST', body: JSON.stringify({ proposal_id }),
      }),
  },

  paymentLinks: {
    list: () => request<Record<string, unknown>[]>('/payment-links'),
    create: (proposal_id: string, custom_amount?: number) =>
      request<{ url: string }>('/payment-links', {
        method: 'POST', body: JSON.stringify({ proposal_id, custom_amount }),
      }),
  },

  clients: {
    list:   () => request<Client[]>('/clients'),
    demo:   () => request<Client[]>('/clients/demo'),
    detail: (id: string) => request<ClientDetail>(`/clients/${id}/detail`),
  },

  followUps: {
    list: (proposal_id?: string) =>
      request<Record<string, unknown>[]>(proposal_id ? `/follow-ups?proposal_id=${proposal_id}` : '/follow-ups'),
    schedule: (proposal_id: string) =>
      request<{ scheduled: number; entries: Record<string, unknown>[] }>('/follow-ups/schedule', {
        method: 'POST', body: JSON.stringify({ proposal_id }),
      }),
    process: () => request<{ processed: number }>('/follow-ups/process', { method: 'POST' }),
    cancel: (id: string) => request<{ cancelled: boolean }>(`/follow-ups/${id}/cancel`, { method: 'DELETE' }),
    log: () => request<Record<string, unknown>[]>('/follow-ups/log'),
  },

  analytics: {
    summary: (period_days = 30) =>
      request<{
        period_days: number; pipeline_value: number; revenue_realized: number; roi_pct: number;
        proposals_generated: number; proposals_sent: number; proposals_accepted: number;
        proposals_ignored: number; proposals_rejected: number; escalations: number;
        acceptance_rate: number; clients_reached: number; follow_ups_sent: number;
        time_saved_hours: number;
        by_type: { opportunity_type: string; proposals: number; accepted: number; revenue: number }[];
        weekly_trend: { week_start: string; sent: number; accepted: number; acceptance_rate: number; revenue: number }[];
      }>(`/analytics/summary?period_days=${period_days}`),
    snapshot: () => request<Record<string, unknown>>('/analytics/snapshot', { method: 'POST' }),
    snapshots: (limit = 12) => request<Record<string, unknown>[]>(`/analytics/snapshots?limit=${limit}`),
  },

  churn: {
    scan: () => request<{ escalated: number; records: Record<string, unknown>[] }>('/churn/scan', { method: 'POST' }),
    escalations: (limit = 50) => request<Record<string, unknown>[]>(`/churn/escalations?limit=${limit}`),
    log: () => request<Record<string, unknown>[]>('/churn/log'),
  },

  crm: {
    syncLog: (limit = 50) => request<Record<string, unknown>[]>(`/crm/sync-log?limit=${limit}`),
    log: () => request<Record<string, unknown>[]>('/crm/log'),
    sync: (proposal_id: string, client_id: string, revenue: number, opportunity_type: string) =>
      request<{ ok: boolean }>('/crm/sync', {
        method: 'POST', body: JSON.stringify({ proposal_id, client_id, revenue, opportunity_type }),
      }),
  },

  seasonal: {
    upcoming: (weeks = 8) => request<{ name: string; date: string; days_away: number; types: string[]; current_boost: number }[]>(`/seasonal/upcoming?weeks=${weeks}`),
    boosts: () => request<{ opportunity_type: string; multiplier: number; months: number[] }[]>('/seasonal/boosts'),
    updatePropensity: () => request<{ updated: boolean; counts: Record<string, number> }>('/propensity/update', { method: 'POST' }),
    propensityClients: () => request<Record<string, unknown>[]>('/propensity/clients'),
    updateChannel: (client_id: string, channel: string, whatsapp_number?: string) =>
      request<{ updated: boolean }>('/clients/channel', {
        method: 'PATCH', body: JSON.stringify({ client_id, channel, whatsapp_number }),
      }),
    whatsappLog: () => request<Record<string, unknown>[]>('/whatsapp/log'),
  },
}
