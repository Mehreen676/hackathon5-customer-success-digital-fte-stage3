'use client'

import { useState } from 'react'
import api from '@/lib/api'

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

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  open: { label: 'Open', color: 'bg-blue-100 text-blue-700 border-blue-200' },
  'auto-resolved': { label: 'Auto-Resolved', color: 'bg-green-100 text-green-700 border-green-200' },
  escalated: { label: 'Escalated', color: 'bg-red-100 text-red-700 border-red-200' },
  pending_review: { label: 'Pending Review', color: 'bg-yellow-100 text-yellow-700 border-yellow-200' },
  closed: { label: 'Closed', color: 'bg-gray-100 text-gray-600 border-gray-200' },
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'text-red-700 font-semibold',
  high: 'text-orange-600 font-semibold',
  medium: 'text-yellow-700',
  low: 'text-green-700',
}

const CHANNEL_ICONS: Record<string, string> = {
  email: '📧',
  whatsapp: '💬',
  web_form: '🌐',
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

export default function TicketStatusLookup() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [ticket, setTicket] = useState<TicketStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  const normalise = (val: string) => val.trim().toUpperCase()

  async function handleLookup(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setTicket(null)

    const ref = normalise(query)
    if (!ref) {
      setError('Enter a ticket reference, e.g. TKT-A1B2C3D4')
      return
    }
    if (!/^TKT-[A-Z0-9]{6,8}$/.test(ref)) {
      setError('Ticket references look like TKT-A1B2C3D4. Please check and try again.')
      return
    }

    setLoading(true)
    try {
      const data = await api.getTicketStatus(ref) as TicketStatus
      setTicket(data)
    } catch (err: any) {
      if (err?.message?.includes('404')) {
        setError(`No ticket found for reference ${ref}. Double-check the reference and try again.`)
      } else {
        setError('Could not reach the support system. Please try again later.')
      }
    } finally {
      setLoading(false)
    }
  }

  const statusInfo = ticket ? (STATUS_LABELS[ticket.status] ?? { label: ticket.status, color: 'bg-gray-100 text-gray-600 border-gray-200' }) : null

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 max-w-xl mx-auto">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900">Check Ticket Status</h2>
        <p className="text-sm text-gray-500 mt-1">
          Enter the ticket reference from your submission confirmation.
        </p>
      </div>

      <form onSubmit={handleLookup} className="flex gap-3 mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setError(null)
          }}
          placeholder="TKT-A1B2C3D4"
          className="flex-1 px-4 py-2.5 rounded-xl border border-gray-300 text-sm font-mono
                     focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent
                     hover:border-gray-400 transition-colors uppercase"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-5 py-2.5 bg-purple-600 text-white text-sm font-medium rounded-xl
                     hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed
                     transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
        >
          {loading ? (
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          ) : (
            'Look up'
          )}
        </button>
      </form>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 mb-4">
          {error}
        </div>
      )}

      {/* Ticket result */}
      {ticket && statusInfo && (
        <div className="space-y-4 animate-in fade-in duration-300">
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Ticket</p>
              <p className="font-mono font-bold text-purple-700 text-xl">{ticket.ticket_ref}</p>
            </div>
            <span
              className={`text-xs font-medium px-3 py-1.5 rounded-full border ${statusInfo.color}`}
            >
              {statusInfo.label}
            </span>
          </div>

          {/* Details grid */}
          <div className="bg-gray-50 rounded-xl p-4 space-y-3 text-sm">
            <Row label="Subject" value={ticket.subject} />
            <Row
              label="Channel"
              value={`${CHANNEL_ICONS[ticket.channel] ?? '📝'} ${ticket.channel.replace('_', ' ')}`}
            />
            <Row
              label="Priority"
              valueClass={PRIORITY_COLORS[ticket.priority]}
              value={ticket.priority.charAt(0).toUpperCase() + ticket.priority.slice(1)}
            />
            <Row label="Customer" value={ticket.customer_name} />
            <Row label="Submitted" value={formatDate(ticket.created_at)} />
            {ticket.assigned_team && (
              <Row label="Assigned to" value={ticket.assigned_team} />
            )}
            {ticket.escalation_reason && (
              <Row
                label="Escalation reason"
                value={ticket.escalation_reason.replace(/_/g, ' ')}
                valueClass="text-red-700"
              />
            )}
          </div>

          {/* Latest agent response */}
          {ticket.latest_response && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Latest response
              </p>
              <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                {ticket.latest_response}
              </div>
            </div>
          )}

          {/* Look up another */}
          <button
            onClick={() => { setTicket(null); setQuery('') }}
            className="w-full py-2.5 px-4 rounded-xl border border-gray-300 text-sm text-gray-700
                       hover:bg-gray-50 transition-colors"
          >
            Look up another ticket
          </button>
        </div>
      )}

      {/* Hint */}
      {!ticket && !error && (
        <p className="text-xs text-gray-400 text-center">
          Ticket references are included in your submission confirmation email and
          in the response shown after submitting a request above.
        </p>
      )}
    </div>
  )
}

function Row({
  label,
  value,
  valueClass,
}: {
  label: string
  value: string
  valueClass?: string
}) {
  return (
    <div className="flex justify-between items-start gap-4">
      <span className="text-gray-500 shrink-0">{label}</span>
      <span className={`text-right ${valueClass ?? 'text-gray-900'}`}>{value}</span>
    </div>
  )
}
