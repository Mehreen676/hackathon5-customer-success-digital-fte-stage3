'use client'

import { useState } from 'react'
import { Send, Paperclip, Smile, X } from 'lucide-react'

interface Ticket {
  ticket_ref: string
  customer: string
  initials: string
  subject: string
  priority: 'critical' | 'high' | 'medium' | 'low'
  status: 'open' | 'escalated' | 'auto-resolved' | 'resolved' | 'closed' | 'pending_review'
  channel: 'email' | 'whatsapp' | 'web_form'
  escalated: boolean
  created_at: string
  description?: string
}

const MOCK_TICKETS: Ticket[] = [
  { ticket_ref: 'TKT-0048', customer: 'James Liu',     initials: 'JL', subject: '[REFUND] Charged twice for subscription',  priority: 'high',     status: 'escalated',      channel: 'whatsapp', escalated: true,  created_at: '2026-03-14 10:15', description: 'Customer reports duplicate charge for March billing cycle.' },
  { ticket_ref: 'TKT-0047', customer: 'Sarah Chen',    initials: 'SC', subject: '[BILLING] Invoice not accessible',          priority: 'low',      status: 'auto-resolved',  channel: 'email',    escalated: false, created_at: '2026-03-14 10:21', description: 'Customer could not find invoice. Resolved via KB article.' },
  { ticket_ref: 'TKT-0046', customer: 'Priya Sharma',  initials: 'PS', subject: '[ACCOUNT] SSO setup assistance',            priority: 'medium',   status: 'resolved',       channel: 'web_form', escalated: false, created_at: '2026-03-14 09:10', description: 'Enterprise SSO SAML 2.0 configuration walkthrough.' },
  { ticket_ref: 'TKT-0045', customer: 'Ahmed Al-Farsi',initials: 'AA', subject: '[LEGAL] Attorney involved in dispute',      priority: 'critical', status: 'escalated',      channel: 'email',    escalated: true,  created_at: '2026-03-13 16:42', description: 'Legal complaint — escalated to Legal & CS team immediately.' },
  { ticket_ref: 'TKT-0044', customer: 'Linda Wong',    initials: 'LW', subject: '[INTEGRATION] Slack connection failing',   priority: 'medium',   status: 'pending_review', channel: 'email',    escalated: false, created_at: '2026-03-13 14:20', description: 'Slack OAuth integration returning 401 errors.' },
  { ticket_ref: 'TKT-0043', customer: 'Carlos Rivera', initials: 'CR', subject: '[PLAN] Enterprise pricing inquiry',         priority: 'low',      status: 'escalated',      channel: 'web_form', escalated: true,  created_at: '2026-03-13 11:05', description: 'Pricing negotiation — escalated to Sales team.' },
]

const PRIORITY_BADGE: Record<string, string> = {
  critical: 'badge-red',
  high:     'badge-orange',
  medium:   'badge-yellow',
  low:      'badge-blue',
}

const STATUS_BADGE: Record<string, string> = {
  open:           'badge-blue',
  escalated:      'badge-red',
  'auto-resolved':'badge-green',
  resolved:       'badge-green',
  closed:         'badge-gray',
  pending_review: 'badge-yellow',
}

const CHANNEL_BADGE: Record<string, { label: string; cls: string }> = {
  email:    { label: 'Email',    cls: 'badge-blue'  },
  whatsapp: { label: 'WA',       cls: 'badge-green' },
  web_form: { label: 'Web',      cls: 'badge-cyan'  },
}

type Filter = 'all' | 'open' | 'escalated' | 'resolved'

export default function TicketPanel() {
  const [filter, setFilter] = useState<Filter>('all')
  const [selected, setSelected] = useState<Ticket | null>(null)
  const [reply, setReply] = useState('')

  const filtered = MOCK_TICKETS.filter((t) => {
    if (filter === 'open')      return ['open', 'pending_review'].includes(t.status)
    if (filter === 'escalated') return t.escalated
    if (filter === 'resolved')  return ['resolved', 'auto-resolved', 'closed'].includes(t.status)
    return true
  })

  const filters: { key: Filter; label: string; count: number }[] = [
    { key: 'all',       label: 'All',       count: MOCK_TICKETS.length },
    { key: 'open',      label: 'Open',      count: MOCK_TICKETS.filter((t) => ['open', 'pending_review'].includes(t.status)).length },
    { key: 'escalated', label: 'Escalated', count: MOCK_TICKETS.filter((t) => t.escalated).length },
    { key: 'resolved',  label: 'Resolved',  count: MOCK_TICKETS.filter((t) => ['resolved', 'auto-resolved', 'closed'].includes(t.status)).length },
  ]

  return (
    <div className="flex gap-4 h-full">
      {/* Ticket list */}
      <div className="flex-1 flex flex-col gap-4 min-w-0">
        {/* Filter tabs */}
        <div className="flex gap-2">
          {filters.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
              style={
                filter === f.key
                  ? { background: 'rgba(139,92,246,0.25)', color: '#a78bfa', border: '1px solid rgba(167,139,250,0.3)' }
                  : { background: 'rgba(255,255,255,0.04)', color: '#6b7280', border: '1px solid rgba(255,255,255,0.06)' }
              }
            >
              {f.label}
              <span
                className="ml-2 px-1.5 py-0.5 rounded-full text-[10px]"
                style={
                  filter === f.key
                    ? { background: 'rgba(139,92,246,0.4)', color: '#c4b5fd' }
                    : { background: 'rgba(255,255,255,0.06)', color: '#6b7280' }
                }
              >
                {f.count}
              </span>
            </button>
          ))}
        </div>

        {/* Table */}
        <div className="card-dark p-0 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr>
                <th className="th-dark text-left">Ticket</th>
                <th className="th-dark text-left">Customer</th>
                <th className="th-dark text-left">Subject</th>
                <th className="th-dark text-left">Priority</th>
                <th className="th-dark text-left">Status</th>
                <th className="th-dark text-left">Channel</th>
                <th className="th-dark text-left">Created</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((ticket) => {
                const isSelected = selected?.ticket_ref === ticket.ticket_ref
                const ch = CHANNEL_BADGE[ticket.channel]
                return (
                  <tr
                    key={ticket.ticket_ref}
                    onClick={() => setSelected(isSelected ? null : ticket)}
                    className="cursor-pointer transition-all"
                    style={{
                      background: isSelected ? 'rgba(139,92,246,0.08)' : 'transparent',
                    }}
                    onMouseEnter={(e) => { if (!isSelected) (e.currentTarget as HTMLTableRowElement).style.background = 'rgba(255,255,255,0.03)' }}
                    onMouseLeave={(e) => { if (!isSelected) (e.currentTarget as HTMLTableRowElement).style.background = 'transparent' }}
                  >
                    <td className="td-dark font-mono text-xs font-semibold" style={{ color: '#a78bfa' }}>{ticket.ticket_ref}</td>
                    <td className="td-dark">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0"
                          style={{ background: 'linear-gradient(135deg,#7c3aed,#3b82f6)' }}
                        >
                          {ticket.initials}
                        </div>
                        <span className="text-sm font-medium text-gray-200">{ticket.customer}</span>
                      </div>
                    </td>
                    <td className="td-dark text-gray-400 max-w-xs truncate text-xs">{ticket.subject}</td>
                    <td className="td-dark"><span className={`badge-dark ${PRIORITY_BADGE[ticket.priority]}`}>{ticket.priority}</span></td>
                    <td className="td-dark"><span className={`badge-dark ${STATUS_BADGE[ticket.status]}`}>{ticket.status}</span></td>
                    <td className="td-dark"><span className={`badge-dark ${ch.cls}`}>{ch.label}</span></td>
                    <td className="td-dark text-xs text-gray-600">{ticket.created_at}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail + AI reply panel */}
      {selected && (
        <div className="flex-shrink-0 flex flex-col gap-4" style={{ width: 280 }}>
          {/* Ticket details */}
          <div className="card-glow-purple">
            <div className="flex items-center justify-between mb-4">
              <span className="font-mono text-xs font-semibold" style={{ color: '#a78bfa' }}>{selected.ticket_ref}</span>
              <button onClick={() => setSelected(null)} className="btn-ghost p-1">
                <X size={14} />
              </button>
            </div>
            <div className="space-y-2.5 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500 text-xs">Customer</span>
                <span className="text-gray-200 text-xs font-medium">{selected.customer}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-500 text-xs">Priority</span>
                <span className={`badge-dark ${PRIORITY_BADGE[selected.priority]}`}>{selected.priority}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-500 text-xs">Status</span>
                <span className={`badge-dark ${STATUS_BADGE[selected.status]}`}>{selected.status}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-500 text-xs">Channel</span>
                <span className={`badge-dark ${CHANNEL_BADGE[selected.channel].cls}`}>{CHANNEL_BADGE[selected.channel].label}</span>
              </div>
              {selected.escalated && (
                <div
                  className="p-2.5 rounded-lg text-xs"
                  style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#f87171' }}
                >
                  Escalated to specialist team
                </div>
              )}
              {selected.description && (
                <div>
                  <p className="text-gray-600 text-xs uppercase tracking-wider mb-1">Description</p>
                  <p className="text-gray-400 text-xs">{selected.description}</p>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-500 text-xs">Created</span>
                <span className="text-gray-600 text-xs">{selected.created_at}</span>
              </div>
            </div>
          </div>

          {/* AI Reply box */}
          <div className="card-dark">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">AI Reply</p>
            <textarea
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              placeholder="Type response…"
              rows={4}
              className="input-dark resize-none mb-3 text-xs"
            />
            <div className="flex items-center gap-2">
              <button className="btn-primary flex items-center gap-1.5 text-xs py-1.5">
                <Send size={12} />
                Send Reply
              </button>
              <button className="btn-ghost p-1.5" title="Attach"><Paperclip size={12} /></button>
              <button className="btn-ghost p-1.5" title="Emoji"><Smile size={12} /></button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
