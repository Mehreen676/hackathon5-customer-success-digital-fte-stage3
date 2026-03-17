'use client'

import { useEffect, useState } from 'react'
import { Send, Paperclip, Smile, X, RefreshCw } from 'lucide-react'
import api from '../lib/api'
import type { TicketListItem } from '../lib/api'

interface Ticket extends TicketListItem {
  avatar: string
}

function avatarUrl(name: string): string {
  let hash = 0
  for (const c of name) hash = (hash * 31 + c.charCodeAt(0)) & 0xffff
  return `https://i.pravatar.cc/150?img=${(hash % 70) + 1}`
}

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
  email:    { label: 'Email', cls: 'badge-blue'  },
  whatsapp: { label: 'WA',    cls: 'badge-green' },
  web_form: { label: 'Web',   cls: 'badge-cyan'  },
}

type Filter = 'all' | 'open' | 'escalated' | 'resolved'

export default function TicketPanel() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<Filter>('all')
  const [selected, setSelected] = useState<Ticket | null>(null)
  const [reply, setReply] = useState('')

  const fetchTickets = async () => {
    setLoading(true)
    try {
      const data = await api.getTickets(50)
      setTickets(data.map((t) => ({ ...t, avatar: avatarUrl(t.customer) })))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTickets()
  }, [])

  const filtered = tickets.filter((t) => {
    if (filter === 'open')      return ['open', 'pending_review'].includes(t.status)
    if (filter === 'escalated') return t.escalated
    if (filter === 'resolved')  return ['resolved', 'auto-resolved', 'closed'].includes(t.status)
    return true
  })

  const filters: { key: Filter; label: string; count: number }[] = [
    { key: 'all',       label: 'All',       count: tickets.length },
    { key: 'open',      label: 'Open',      count: tickets.filter((t) => ['open', 'pending_review'].includes(t.status)).length },
    { key: 'escalated', label: 'Escalated', count: tickets.filter((t) => t.escalated).length },
    { key: 'resolved',  label: 'Resolved',  count: tickets.filter((t) => ['resolved', 'auto-resolved', 'closed'].includes(t.status)).length },
  ]

  return (
    <div className="flex gap-5 h-full">
      {/* Ticket list */}
      <div className="flex-1 flex flex-col gap-5 min-w-0">
        {/* Filter tabs + refresh */}
        <div className="flex items-center gap-2.5">
          {filters.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className="px-5 py-2.5 rounded-xl text-sm font-semibold transition-all"
              style={
                filter === f.key
                  ? { background: 'rgba(139,92,246,0.25)', color: '#a78bfa', border: '1px solid rgba(167,139,250,0.3)' }
                  : { background: 'rgba(255,255,255,0.04)', color: '#6b7280', border: '1px solid rgba(255,255,255,0.06)' }
              }
            >
              {f.label}
              <span
                className="ml-2 px-2 py-0.5 rounded-full text-xs"
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
          <button
            onClick={fetchTickets}
            disabled={loading}
            className="ml-auto btn-ghost"
            title="Refresh tickets"
          >
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>

        {/* Table */}
        <div className="card p-0 overflow-hidden">
          {loading && tickets.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-gray-500 text-sm gap-2">
              <RefreshCw size={16} className="animate-spin" />
              Loading tickets…
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-gray-500 text-sm">
              No tickets found.
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr>
                  <th className="th text-left">Ticket</th>
                  <th className="th text-left">Customer</th>
                  <th className="th text-left">Subject</th>
                  <th className="th text-left">Priority</th>
                  <th className="th text-left">Status</th>
                  <th className="th text-left">Channel</th>
                  <th className="th text-left">Created</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((ticket) => {
                  const isSelected = selected?.ticket_ref === ticket.ticket_ref
                  const ch = CHANNEL_BADGE[ticket.channel] ?? { label: ticket.channel, cls: 'badge-gray' }
                  return (
                    <tr
                      key={ticket.ticket_ref}
                      onClick={() => setSelected(isSelected ? null : ticket)}
                      className="cursor-pointer transition-all"
                      style={{ background: isSelected ? 'rgba(139,92,246,0.1)' : 'transparent' }}
                      onMouseEnter={(e) => { if (!isSelected) (e.currentTarget as HTMLTableRowElement).style.background = 'rgba(255,255,255,0.03)' }}
                      onMouseLeave={(e) => { if (!isSelected) (e.currentTarget as HTMLTableRowElement).style.background = 'transparent' }}
                    >
                      <td className="td font-mono text-xs font-bold" style={{ color: '#a78bfa' }}>{ticket.ticket_ref}</td>
                      <td className="td">
                        <div className="flex items-center gap-2.5">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={ticket.avatar}
                            alt={ticket.customer}
                            className="rounded-full object-cover flex-shrink-0"
                            style={{ width: 38, height: 38, border: '2px solid rgba(167,139,250,0.3)' }}
                          />
                          <span className="text-sm font-semibold text-gray-100">{ticket.customer}</span>
                        </div>
                      </td>
                      <td className="td text-gray-400 max-w-xs truncate text-sm">{ticket.subject}</td>
                      <td className="td"><span className={PRIORITY_BADGE[ticket.priority] ?? 'badge-gray'}>{ticket.priority}</span></td>
                      <td className="td"><span className={STATUS_BADGE[ticket.status] ?? 'badge-gray'}>{ticket.status}</span></td>
                      <td className="td"><span className={ch.cls}>{ch.label}</span></td>
                      <td className="td text-xs text-gray-500">{ticket.created_at}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Detail + AI reply panel */}
      {selected && (
        <div className="flex-shrink-0 flex flex-col gap-5" style={{ width: 360 }}>
          {/* Ticket details */}
          <div className="card" style={{ borderTop: '2px solid rgba(129,140,248,0.4)' }}>
            <div className="flex items-center justify-between mb-5">
              <span className="font-mono text-base font-bold" style={{ color: '#a78bfa' }}>{selected.ticket_ref}</span>
              <button onClick={() => setSelected(null)} className="btn-ghost">
                <X size={17} />
              </button>
            </div>
            {/* Customer profile row */}
            <div className="flex items-center gap-4 mb-5 pb-5" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={selected.avatar}
                alt={selected.customer}
                className="rounded-full object-cover flex-shrink-0"
                style={{ width: 56, height: 56, border: '2px solid rgba(167,139,250,0.45)' }}
              />
              <div>
                <p className="text-base font-bold text-white">{selected.customer}</p>
                <p className="text-sm text-gray-500 mt-0.5">Customer · {selected.channel.replace('_', ' ')}</p>
              </div>
            </div>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-500 text-sm font-medium">Priority</span>
                <span className={PRIORITY_BADGE[selected.priority] ?? 'badge-gray'}>{selected.priority}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-500 text-sm font-medium">Status</span>
                <span className={STATUS_BADGE[selected.status] ?? 'badge-gray'}>{selected.status}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-500 text-sm font-medium">Channel</span>
                <span className={`${(CHANNEL_BADGE[selected.channel] ?? { cls: 'badge-gray' }).cls}`}>
                  {(CHANNEL_BADGE[selected.channel] ?? { label: selected.channel }).label}
                </span>
              </div>
              {selected.escalated && (
                <div
                  className="p-4 rounded-xl text-sm font-medium"
                  style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#f87171' }}
                >
                  Escalated to specialist team
                </div>
              )}
              {selected.description && (
                <div className="pt-1">
                  <p className="text-gray-500 text-xs font-semibold uppercase tracking-wider mb-2">Description</p>
                  <p className="text-gray-300 text-sm leading-relaxed">{selected.description}</p>
                </div>
              )}
              <div className="flex justify-between items-center pt-1">
                <span className="text-gray-500 text-sm font-medium">Created</span>
                <span className="text-gray-500 text-sm">{selected.created_at}</span>
              </div>
            </div>
          </div>

          {/* AI Reply box */}
          <div className="card">
            <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-5">AI Reply</p>
            <textarea
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              placeholder="Type response…"
              rows={5}
              className="input-dark resize-none mb-5"
            />
            <div className="flex items-center gap-3">
              <button className="btn-primary">
                <Send size={15} />
                Send Reply
              </button>
              <button className="btn-ghost" title="Attach"><Paperclip size={17} /></button>
              <button className="btn-ghost" title="Emoji"><Smile size={17} /></button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
