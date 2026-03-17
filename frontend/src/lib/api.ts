/**
 * API client — Nexora Support Dashboard (Stage 3)
 *
 * All requests are proxied through Next.js rewrites:
 *   /api/backend/* → http://localhost:8000/*
 */

const BASE_URL = '/api/backend'

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }

  return res.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string
  version: string
  stage: string | number
  db: string
}

export const api = {
  health: () => request<HealthResponse>('/health'),

  // -------------------------------------------------------------------------
  // Support channels
  // -------------------------------------------------------------------------
  sendEmail: (payload: {
    from_email: string
    from_name: string
    subject: string
    body: string
    customer_id?: string
  }) => request('/support/gmail', { method: 'POST', body: JSON.stringify(payload) }),

  sendWhatsApp: (payload: {
    from_phone: string
    message_text: string
    customer_id?: string
  }) => request('/support/whatsapp', { method: 'POST', body: JSON.stringify(payload) }),

  sendWebForm: (payload: {
    name: string
    email: string
    subject: string
    message: string
    customer_id?: string
  }) => request('/support/webform', { method: 'POST', body: JSON.stringify(payload) }),

  sendMessage: (payload: {
    customer_id: string
    channel: string
    content: string
    metadata?: Record<string, unknown>
  }) => request('/support/message', { method: 'POST', body: JSON.stringify(payload) }),

  // -------------------------------------------------------------------------
  // Support form (public-facing /support page)
  // -------------------------------------------------------------------------
  submitSupportForm: (payload: {
    name: string
    email: string
    subject: string
    message: string
    customer_id?: string
  }) => request('/support/submit', { method: 'POST', body: JSON.stringify(payload) }),

  getTicketStatus: (ticketRef: string) =>
    request(`/support/ticket/${encodeURIComponent(ticketRef)}`),

  // -------------------------------------------------------------------------
  // Analytics
  // -------------------------------------------------------------------------
  getAnalyticsSummary: () =>
    request('/analytics/summary').catch(() => _demoAnalytics()),

  getUsageStats: () =>
    request('/analytics/usage').catch(() => null),

  getRecentInteractions: (limit = 20) =>
    request(`/analytics/recent?limit=${limit}`).catch(() => ({ records: [], source: 'error' })),
}

// Demo fallback so dashboard works without backend running
function _demoAnalytics() {
  return {
    total_interactions: 1247,
    avg_response_time_ms: 342.5,
    escalation_rate: 0.12,
    kb_hit_rate: 0.68,
    ai_usage_rate: 0.20,
    fallback_rate: 0.08,
    ticket_creation_rate: 0.94,
    interactions_by_channel: { email: 587, whatsapp: 412, web_form: 248 },
    interactions_by_intent: {
      billing: 312, account: 287, integration: 198,
      general: 176, plan: 143, data: 67, team: 64,
    },
    interactions_by_source: { kb: 848, llm: 249, fallback: 100, escalation: 50 },
    total_tokens_used: 284500,
    source: 'demo',
  }
}

export default api
