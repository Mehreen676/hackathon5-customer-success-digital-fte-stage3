/**
 * API client — Nexora Support Dashboard (Stage 3)
 *
 * When NEXT_PUBLIC_API_URL is set to a full URL (e.g. the HF Spaces URL on
 * Vercel), the client calls the backend directly from the browser (CORS is
 * allowed via allow_origins=["*"]).
 *
 * When NEXT_PUBLIC_API_URL is not set or is a relative path, requests go
 * through the Next.js /api/backend/* proxy rewrite (local development).
 */

const _envUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
const BASE_URL = _envUrl.startsWith('http') ? _envUrl : '/api/backend'

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

export interface TicketListItem {
  ticket_ref: string
  customer: string
  subject: string
  priority: string
  status: string
  channel: string
  escalated: boolean
  created_at: string
  description?: string
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

  getTickets: (limit = 50) =>
    request<TicketListItem[]>(`/support/tickets?limit=${limit}`).catch(() => [] as TicketListItem[]),

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

// Empty-state fallback — used when the backend is unreachable.
// Returns all zeros so the UI shows real empty states instead of fake data.
function _demoAnalytics() {
  return {
    total_interactions: 0,
    avg_response_time_ms: 0,
    escalation_rate: 0,
    kb_hit_rate: 0,
    ai_usage_rate: 0,
    fallback_rate: 0,
    ticket_creation_rate: 0,
    interactions_by_channel: {} as Record<string, number>,
    interactions_by_intent:  {} as Record<string, number>,
    interactions_by_source:  {} as Record<string, number>,
    total_tokens_used: 0,
    source: 'empty',
  }
}

export default api
