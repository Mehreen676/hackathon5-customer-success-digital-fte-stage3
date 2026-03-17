'use client'

import { useState } from 'react'
import { Search, RefreshCw, AlertCircle, X } from 'lucide-react'
import api from '../lib/api'

// ─── Types ───────────────────────────────────────────────────────────────────

interface TicketStatus {
  ticket_ref: string
  status: string
  priority: string
  escalated: boolean
  channel: string
  subject: string
  created_at: string
  customer_name: string
  assigned_team: string | null
  escalation_reason: string | null
  latest_response: string | null
}

// ─── Maps ────────────────────────────────────────────────────────────────────

const STATUS_STYLE: Record<string, { bg: string; color: string; border: string; label: string }> = {
  'open':          { bg: 'rgba(37,99,235,0.12)',  color: '#93C5FD', border: 'rgba(37,99,235,0.25)',  label: 'Open' },
  'auto-resolved': { bg: 'rgba(5,150,105,0.12)',  color: '#6EE7B7', border: 'rgba(5,150,105,0.25)',  label: 'Auto-Resolved' },
  'escalated':     { bg: 'rgba(220,38,38,0.12)',  color: '#FCA5A5', border: 'rgba(220,38,38,0.25)',  label: 'Escalated' },
  'pending_review':{ bg: 'rgba(217,119,6,0.12)',  color: '#FCD34D', border: 'rgba(217,119,6,0.25)',  label: 'Pending Review' },
  'closed':        { bg: 'rgba(100,116,139,0.1)', color: '#94A3B8', border: 'rgba(100,116,139,0.2)', label: 'Closed' },
}

const PRIORITY_COLOR: Record<string, string> = {
  critical: '#FCA5A5',
  high:     '#FDBA74',
  medium:   '#FCD34D',
  low:      '#86EFAC',
}

const CHANNEL_ICON: Record<string, string> = {
  email: '📧', whatsapp: '💬', web_form: '🌐',
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(iso))
  } catch { return iso }
}

function inputBase(): React.CSSProperties {
  return {
    flex: 1, padding: '11px 14px', borderRadius: 10,
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.09)',
    color: '#E2E8F0', fontSize: 14,
    outline: 'none', fontFamily: 'monospace', textTransform: 'uppercase',
    transition: 'border-color .15s, box-shadow .15s',
    colorScheme: 'dark' as React.CSSProperties['colorScheme'],
  }
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function TicketStatusLookup() {
  const [query,   setQuery]   = useState('')
  const [loading, setLoading] = useState(false)
  const [ticket,  setTicket]  = useState<TicketStatus | null>(null)
  const [error,   setError]   = useState<string | null>(null)

  async function handleLookup(e: React.FormEvent) {
    e.preventDefault()
    setError(null); setTicket(null)
    const ref = query.trim().toUpperCase()
    if (!ref) { setError('Enter a ticket reference, e.g. TKT-A1B2C3D4'); return }
    if (!/^TKT-[A-Z0-9]{6,8}$/.test(ref)) { setError('Ticket references look like TKT-A1B2C3D4. Please check and try again.'); return }

    setLoading(true)
    try {
      const data = await api.getTicketStatus(ref) as TicketStatus
      setTicket(data)
    } catch (err: any) {
      setError(
        err?.message?.includes('404')
          ? `No ticket found for ${ref}. Double-check the reference and try again.`
          : 'Could not reach the support system. Please try again later.'
      )
    } finally { setLoading(false) }
  }

  const st = ticket ? (STATUS_STYLE[ticket.status] ?? STATUS_STYLE.closed) : null

  return (
    <div style={{
      borderRadius: 18, padding: '24px 24px',
      background: '#111827',
      border: '1px solid rgba(255,255,255,0.07)',
      borderTop: '3px solid #2563EB',
    }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 17, fontWeight: 700, color: '#F1F5F9', marginBottom: 4 }}>Check Ticket Status</h2>
        <p style={{ fontSize: 13, color: '#64748B' }}>
          Enter the ticket reference from your submission confirmation.
        </p>
      </div>

      {/* Search bar */}
      <form onSubmit={handleLookup} style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
        <input
          type="text"
          value={query}
          onChange={e => { setQuery(e.target.value); setError(null) }}
          placeholder="TKT-A1B2C3D4"
          style={inputBase()}
          onFocus={e => {
            e.target.style.borderColor = 'rgba(37,99,235,0.5)'
            e.target.style.boxShadow   = '0 0 0 3px rgba(37,99,235,0.08)'
          }}
          onBlur={e => {
            e.target.style.borderColor = 'rgba(255,255,255,0.09)'
            e.target.style.boxShadow   = 'none'
          }}
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          style={{
            padding: '11px 18px', borderRadius: 10, flexShrink: 0,
            background: loading || !query.trim()
              ? 'rgba(37,99,235,0.3)'
              : 'linear-gradient(135deg,#2563EB,#1D4ED8)',
            border: '1px solid rgba(37,99,235,0.4)',
            color: '#fff', fontSize: 14, fontWeight: 600,
            cursor: loading || !query.trim() ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', gap: 7,
            transition: 'transform .18s, box-shadow .18s',
          }}
          onMouseEnter={e => {
            if (!loading && query.trim()) {
              e.currentTarget.style.transform = 'translateY(-1px)'
              e.currentTarget.style.boxShadow = '0 6px 18px rgba(37,99,235,0.28)'
            }
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = 'none'
          }}
        >
          {loading
            ? <RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} />
            : <><Search size={14} /> Look up</>
          }
        </button>
      </form>

      {/* Error */}
      {error && (
        <div style={{
          display: 'flex', alignItems: 'flex-start', gap: 10,
          padding: '12px 14px', borderRadius: 10, marginBottom: 12,
          background: 'rgba(220,38,38,0.08)',
          border: '1px solid rgba(220,38,38,0.22)',
        }}>
          <AlertCircle size={15} style={{ color: '#F87171', flexShrink: 0, marginTop: 1 }} />
          <span style={{ fontSize: 13, color: '#FCA5A5', lineHeight: 1.5 }}>{error}</span>
        </div>
      )}

      {/* Ticket result */}
      {ticket && st && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Ref + status */}
          <div style={{
            display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12,
            padding: '16px 18px', borderRadius: 12,
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.07)',
          }}>
            <div>
              <p style={{ fontSize: 10.5, color: '#475569', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700, marginBottom: 5 }}>
                Ticket
              </p>
              <p style={{ fontFamily: 'monospace', fontWeight: 800, fontSize: 20, color: '#C4B5FD' }}>
                {ticket.ticket_ref}
              </p>
            </div>
            <span style={{
              padding: '5px 12px', borderRadius: 99, fontSize: 11.5, fontWeight: 700,
              background: st.bg, color: st.color, border: `1px solid ${st.border}`,
            }}>
              {st.label}
            </span>
          </div>

          {/* Details */}
          <div style={{
            borderRadius: 12, padding: '4px 0',
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.06)',
            overflow: 'hidden',
          }}>
            {[
              { label: 'Subject',    value: ticket.subject },
              { label: 'Channel',    value: `${CHANNEL_ICON[ticket.channel] ?? '📝'} ${ticket.channel.replace('_', ' ')}` },
              { label: 'Priority',   value: ticket.priority.charAt(0).toUpperCase() + ticket.priority.slice(1), color: PRIORITY_COLOR[ticket.priority] },
              { label: 'Customer',   value: ticket.customer_name },
              { label: 'Submitted',  value: formatDate(ticket.created_at) },
              ...(ticket.assigned_team ? [{ label: 'Assigned to', value: ticket.assigned_team }] : []),
              ...(ticket.escalation_reason ? [{ label: 'Escalation', value: ticket.escalation_reason.replace(/_/g, ' '), color: '#FCA5A5' }] : []),
            ].map(({ label, value, color }, i, arr) => (
              <div key={label} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12,
                padding: '11px 16px',
                borderBottom: i < arr.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none',
              }}>
                <span style={{ fontSize: 12.5, color: '#64748B', flexShrink: 0 }}>{label}</span>
                <span style={{ fontSize: 12.5, color: color ?? '#CBD5E1', textAlign: 'right', fontWeight: 500 }}>{value}</span>
              </div>
            ))}
          </div>

          {/* Agent response */}
          {ticket.latest_response && (
            <div>
              <p style={{
                fontSize: 10.5, fontWeight: 700, color: '#475569',
                textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 10,
              }}>
                Latest response
              </p>
              <div style={{
                borderRadius: 12, padding: '14px 16px',
                background: 'rgba(124,58,237,0.07)',
                border: '1px solid rgba(124,58,237,0.18)',
                fontSize: 13.5, color: '#CBD5E1',
                lineHeight: 1.7, whiteSpace: 'pre-wrap',
              }}>
                {ticket.latest_response}
              </div>
            </div>
          )}

          {/* Reset */}
          <button
            onClick={() => { setTicket(null); setQuery('') }}
            style={{
              width: '100%', padding: '11px 20px', borderRadius: 10,
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#94A3B8', fontSize: 14, fontWeight: 600,
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
              transition: 'all .15s',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'rgba(124,58,237,0.08)'
              e.currentTarget.style.borderColor = 'rgba(124,58,237,0.25)'
              e.currentTarget.style.color = '#C4B5FD'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'
              e.currentTarget.style.color = '#94A3B8'
            }}
          >
            <X size={13} /> Look up another ticket
          </button>
        </div>
      )}

      {/* Empty hint */}
      {!ticket && !error && (
        <p style={{ fontSize: 12, color: '#334155', textAlign: 'center', lineHeight: 1.6 }}>
          Ticket references are included in your submission confirmation
          and shown after submitting a request.
        </p>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
