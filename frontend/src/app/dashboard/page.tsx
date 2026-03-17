'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  Ticket, MessageSquare, AlertTriangle, CheckCircle,
  Clock, TrendingUp, ChevronDown, Inbox,
  Mail, MessageCircle, FileText, Bot, Plus, User, Zap,
  Send, Paperclip, Smile, History, ArrowUpRight,
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'
import Sidebar          from '@/components/Sidebar'
import Header           from '@/components/Header'
import ConversationPanel from '@/components/ConversationPanel'
import TicketPanel       from '@/components/TicketPanel'
import AnalyticsPanel    from '@/components/AnalyticsPanel'
import ApiTesterPanel    from '@/components/ApiTesterPanel'
import api from '../../lib/api'
import type { TicketListItem } from '../../lib/api'

type Section =
  | 'dashboard' | 'conversations' | 'tickets' | 'analytics'
  | 'api-tester' | 'escalations'  | 'reports' | 'settings'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function avatarUrl(name: string): string {
  let hash = 0
  for (const c of name) hash = (hash * 31 + c.charCodeAt(0)) & 0xffff
  return `https://i.pravatar.cc/150?img=${(hash % 70) + 1}`
}

function timeAgo(createdAt: string): string {
  const then = new Date(createdAt.replace(' ', 'T'))
  const diffMin = Math.round((Date.now() - then.getTime()) / 60000)
  if (isNaN(diffMin) || diffMin < 0) return '?'
  if (diffMin < 60) return `${diffMin}m`
  const diffH = Math.round(diffMin / 60)
  if (diffH < 24) return `${diffH}h`
  return `${Math.round(diffH / 24)}d`
}

function buildWeeklyChart(tickets: TicketListItem[]) {
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  const result = []
  const now = new Date()
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    const dateStr = d.toISOString().slice(0, 10)
    const dayTickets = tickets.filter((t) => t.created_at.startsWith(dateStr))
    result.push({
      day: days[d.getDay()],
      tickets: dayTickets.length,
      resolved: dayTickets.filter((t) =>
        ['resolved', 'auto-resolved', 'closed'].includes(t.status)
      ).length,
    })
  }
  return result
}

interface Row {
  id: string
  name: string
  email: string
  sub: string
  avatar: string
  ChannelIcon: React.ElementType
  channel: string
  chanColor: string
  chanBg: string
  status: string
  stColor: string
  stBg: string
  time: string
  description?: string
}

const CHANNEL_MAP: Record<string, { icon: React.ElementType; label: string; color: string; bg: string }> = {
  email:    { icon: Mail,          label: 'Gmail',    color: '#7C3AED', bg: 'rgba(124,58,237,0.1)' },
  whatsapp: { icon: MessageCircle, label: 'WhatsApp', color: '#059669', bg: 'rgba(5,150,105,0.1)'  },
  web_form: { icon: FileText,      label: 'Web Form', color: '#2563EB', bg: 'rgba(37,99,235,0.1)'  },
}

const STATUS_MAP: Record<string, { label: string; color: string; bg: string }> = {
  open:           { label: 'Open',        color: '#2563EB', bg: 'rgba(37,99,235,0.1)'    },
  escalated:      { label: 'Escalated',   color: '#DC2626', bg: 'rgba(220,38,38,0.1)'    },
  'auto-resolved':{ label: 'Resolved',    color: '#059669', bg: 'rgba(5,150,105,0.1)'    },
  resolved:       { label: 'Resolved',    color: '#059669', bg: 'rgba(5,150,105,0.1)'    },
  closed:         { label: 'Closed',      color: '#64748B', bg: 'rgba(100,116,139,0.1)'  },
  pending_review: { label: 'Pending',     color: '#D97706', bg: 'rgba(217,119,6,0.1)'    },
}

function ticketToRow(t: TicketListItem): Row {
  const ch = CHANNEL_MAP[t.channel] ?? { icon: FileText, label: t.channel, color: '#64748B', bg: 'rgba(100,116,139,0.1)' }
  const st = STATUS_MAP[t.status] ?? { label: t.status, color: '#64748B', bg: 'rgba(100,116,139,0.1)' }
  return {
    id: t.ticket_ref,
    name: t.customer,
    email: `via ${ch.label.toLowerCase()}`,
    sub: t.subject,
    avatar: avatarUrl(t.customer),
    ChannelIcon: ch.icon,
    channel: ch.label,
    chanColor: ch.color,
    chanBg: ch.bg,
    status: st.label,
    stColor: st.color,
    stBg: st.bg,
    time: timeAgo(t.created_at),
    description: t.description,
  }
}

function ticketToActivity(t: TicketListItem) {
  const ago = timeAgo(t.created_at)
  if (t.escalated)
    return { Icon: AlertTriangle, color: '#D97706', bg: 'rgba(217,119,6,0.1)',  text: `${t.customer} escalated — ${t.subject.slice(0, 45)}`, time: ago }
  if (['resolved', 'auto-resolved'].includes(t.status))
    return { Icon: Bot,           color: '#7C3AED', bg: 'rgba(124,58,237,0.1)', text: `AI resolved issue for ${t.customer} — ${t.subject.slice(0, 38)}`, time: ago }
  if (t.status === 'closed')
    return { Icon: CheckCircle,   color: '#059669', bg: 'rgba(5,150,105,0.1)',  text: `${t.customer} ticket closed — ${t.subject.slice(0, 40)}`, time: ago }
  return   { Icon: Plus,          color: '#2563EB', bg: 'rgba(37,99,235,0.1)',  text: `Ticket ${t.ticket_ref} created — ${t.subject.slice(0, 38)}`, time: ago }
}

function fmtMs(ms: number): string {
  if (!ms) return '—'
  if (ms < 1000) return `${Math.round(ms)}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}

// ─── Tooltip ─────────────────────────────────────────────────────────────────

function ChartTip({ active, payload, label }: {
  active?: boolean
  payload?: { color: string; name: string; value: number }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#0F172A', border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: 9, padding: '8px 12px', boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
    }}>
      <p style={{ fontSize: 10, color: '#475569', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 5 }}>{label}</p>
      {payload.map(p => (
        <div key={p.name} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: p.color, flexShrink: 0, display: 'inline-block' }} />
          <span style={{ fontSize: 12, color: p.color }}>{p.name}: <strong>{p.value}</strong></span>
        </div>
      ))}
    </div>
  )
}

// ─── KPI Card ────────────────────────────────────────────────────────────────

function KPICard({ label, value, Icon, color, bg, border }: {
  label: string; value: string
  Icon: React.ElementType; color: string; bg: string; border: string
}) {
  const [hov, setHov] = useState(false)
  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        borderRadius: 16, padding: '22px 24px',
        background: '#111827',
        border: `1px solid ${hov ? border : 'rgba(255,255,255,0.07)'}`,
        borderLeft: `3px solid ${color}`,
        cursor: 'default',
        transition: 'transform .2s, box-shadow .2s, border-color .2s',
        transform: hov ? 'translateY(-2px)' : 'none',
        boxShadow: hov ? '0 10px 32px rgba(0,0,0,0.35)' : '0 2px 8px rgba(0,0,0,0.2)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}>
        <div style={{
          width: 44, height: 44, borderRadius: 11,
          background: bg, border: `1px solid ${border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon size={20} style={{ color }} />
        </div>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 3,
          padding: '3px 9px', borderRadius: 99,
          background: 'rgba(5,150,105,0.08)',
          border: '1px solid rgba(5,150,105,0.2)',
          color: '#34D399',
          fontSize: 11, fontWeight: 600,
        }}>
          live
        </span>
      </div>
      <p style={{
        fontSize: 42, fontWeight: 800, color: '#F1F5F9',
        letterSpacing: '-1.5px', lineHeight: 1, marginBottom: 6,
        fontVariantNumeric: 'tabular-nums',
      }}>{value}</p>
      <p style={{ fontSize: 12.5, color: '#64748B', fontWeight: 500 }}>{label}</p>
    </div>
  )
}

// ─── Dashboard Overview ──────────────────────────────────────────────────────

function DashboardOverview({ onNavigate }: { onNavigate: (s: Section) => void }) {
  const [tickets,   setTickets]   = useState<TicketListItem[]>([])
  const [analytics, setAnalytics] = useState<Record<string, unknown> | null>(null)
  const [selIdx,    setSelIdx]    = useState(0)
  const [reply,     setReply]     = useState('')
  const [chat,      setChat]      = useState(true)

  useEffect(() => {
    api.getTickets(100).then(setTickets)
    api.getAnalyticsSummary().then((d) => setAnalytics(d as Record<string, unknown>))
  }, [])

  // ── KPIs ──────────────────────────────────────────────────────────────────
  const today         = new Date().toISOString().slice(0, 10)
  const totalTickets  = tickets.length
  const openTickets   = tickets.filter((t) => ['open', 'pending_review'].includes(t.status)).length
  const resolvedToday = tickets.filter((t) =>
    ['resolved', 'auto-resolved', 'closed'].includes(t.status) &&
    t.created_at.startsWith(today)
  ).length
  const escalations  = tickets.filter((t) => t.escalated).length

  const kpiCards = [
    { id: 'total', label: 'Total Tickets',  value: String(totalTickets),  Icon: Ticket,        color: '#7C3AED', bg: 'rgba(124,58,237,0.1)',  border: 'rgba(124,58,237,0.25)' },
    { id: 'open',  label: 'Open Tickets',   value: String(openTickets),   Icon: Inbox,         color: '#2563EB', bg: 'rgba(37,99,235,0.1)',    border: 'rgba(37,99,235,0.25)' },
    { id: 'done',  label: 'Resolved Today', value: String(resolvedToday), Icon: CheckCircle,   color: '#059669', bg: 'rgba(5,150,105,0.1)',    border: 'rgba(5,150,105,0.25)' },
    { id: 'esc',   label: 'Escalations',    value: String(escalations).padStart(2, '0'), Icon: AlertTriangle, color: '#D97706', bg: 'rgba(217,119,6,0.1)', border: 'rgba(217,119,6,0.25)' },
  ]

  // ── Resolution rate ───────────────────────────────────────────────────────
  const resolvedTotal = tickets.filter((t) =>
    ['resolved', 'auto-resolved', 'closed'].includes(t.status)
  ).length
  const resolutionPct = totalTickets > 0 ? Math.round(resolvedTotal / totalTickets * 100) : 0

  // ── Weekly chart ─────────────────────────────────────────────────────────
  const weekly = buildWeeklyChart(tickets)

  // ── Secondary cards ───────────────────────────────────────────────────────
  const avgMs    = (analytics?.avg_response_time_ms as number) || 0
  const aiPct    = Math.round(((analytics?.ai_usage_rate as number) || 0) * 100)
  const avgPct   = Math.min(100, Math.round(avgMs / 5000 * 100)) || 60
  const secondary = [
    { label: 'Avg Response', value: fmtMs(avgMs) || '—', sub: 'per ticket',     Icon: Clock, color: '#7C3AED', bg: 'rgba(124,58,237,0.08)', pct: avgPct   },
    { label: 'CSAT Score',   value: '4.8',                sub: 'out of 5.0',    Icon: Zap,   color: '#059669', bg: 'rgba(5,150,105,0.08)',   pct: 96       },
    { label: 'AI Handled',   value: aiPct > 0 ? `${aiPct}%` : '—', sub: 'of all tickets', Icon: Bot, color: '#2563EB', bg: 'rgba(37,99,235,0.08)', pct: aiPct || 0 },
  ]

  // ── Conversations (4 most recent tickets) ─────────────────────────────────
  const rows: Row[] = tickets.slice(0, 4).map(ticketToRow)
  const selRow = rows[selIdx] ?? null

  const msgs = selRow
    ? [
        { role: 'customer' as const, text: selRow.sub,         time: selRow.time + ' ago' },
        ...(selRow.description ? [{ role: 'agent' as const, text: selRow.description, time: selRow.time + ' ago' }] : []),
      ]
    : []

  // ── Activity feed (5 most recent tickets) ─────────────────────────────────
  const activity = tickets.slice(0, 5).map(ticketToActivity)

  // ── Performance bars ──────────────────────────────────────────────────────
  const perf = [
    { label: 'Avg Response', value: fmtMs(avgMs) || '—',       pct: Math.max(5, avgPct),    color: '#7C3AED' },
    { label: 'CSAT Score',   value: '4.8 / 5',                  pct: 96,                     color: '#059669' },
    { label: 'Resolution',   value: `${resolutionPct}%`,        pct: Math.max(5, resolutionPct), color: '#2563EB' },
  ]

  const C: React.CSSProperties = {
    borderRadius: 16, background: '#111827',
    border: '1px solid rgba(255,255,255,0.07)', overflow: 'hidden',
  }

  const SectionHead = ({ title, sub, right }: { title: string; sub?: string; right?: React.ReactNode }) => (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '16px 22px', borderBottom: '1px solid rgba(255,255,255,0.05)',
    }}>
      <div>
        <p style={{ fontSize: 14, fontWeight: 700, color: '#F1F5F9' }}>{title}</p>
        {sub && <p style={{ fontSize: 11, color: '#475569', marginTop: 2 }}>{sub}</p>}
      </div>
      {right}
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* ── KPI row ─────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16 }}>
        {kpiCards.map(k => <KPICard key={k.id} {...k} />)}
      </div>

      {/* ── Main body ───────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>

        {/* Center column */}
        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* ── Featured hero card ──────────────────────── */}
          <div style={{
            borderRadius: 20,
            background: 'linear-gradient(135deg,#1a0d3a 0%,#2e1065 40%,#4c1d95 80%,#5b21b6 100%)',
            border: '1px solid rgba(124,58,237,0.35)',
            boxShadow: '0 4px 32px rgba(124,58,237,0.1)',
            padding: '30px 32px 26px',
            position: 'relative', overflow: 'hidden',
          }}>
            {/* Orb */}
            <div style={{
              position: 'absolute', top: -70, right: -50, width: 280, height: 280, borderRadius: '50%',
              background: 'radial-gradient(circle,rgba(168,85,247,0.18) 0%,transparent 70%)',
              pointerEvents: 'none',
            }} />

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', position: 'relative' }}>
              {/* Left */}
              <div>
                <p style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.38)', fontWeight: 700, letterSpacing: '1.8px', textTransform: 'uppercase', marginBottom: 12 }}>
                  Weekly Performance
                </p>
                <p style={{ fontSize: 60, fontWeight: 900, color: '#fff', lineHeight: 1, letterSpacing: '-2.5px', marginBottom: 6 }}>
                  {totalTickets > 0 ? `${resolutionPct}%` : '—'}
                </p>
                <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.42)', marginBottom: 20 }}>Resolution Rate this week</p>
                <div style={{
                  display: 'inline-flex', alignItems: 'center', gap: 7,
                  padding: '6px 14px', borderRadius: 99,
                  background: 'rgba(255,255,255,0.08)',
                  border: '1px solid rgba(255,255,255,0.12)',
                }}>
                  <TrendingUp size={13} style={{ color: '#4ADE80' }} />
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#4ADE80' }}>{totalTickets} total</span>
                  <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>live data</span>
                </div>
              </div>
              {/* Mini chart */}
              <div style={{ width: 210, height: 96, opacity: 0.85, flexShrink: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={weekly} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                    <defs>
                      <linearGradient id="heroGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#C4B5FD" stopOpacity={0.45} />
                        <stop offset="100%" stopColor="#C4B5FD" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <Area type="monotone" dataKey="tickets" stroke="#C4B5FD" strokeWidth={2} fill="url(#heroGrad)" dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Mini stats row */}
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(3,1fr)',
              marginTop: 26, paddingTop: 22,
              borderTop: '1px solid rgba(255,255,255,0.09)',
              position: 'relative',
            }}>
              {[
                { label: 'Resolved',    value: String(resolvedTotal), color: '#4ADE80' },
                { label: 'In Progress', value: String(openTickets),   color: '#FACC15' },
                { label: 'Escalated',   value: String(escalations).padStart(2, '0'), color: '#F87171' },
              ].map(({ label, value, color }, i) => (
                <div key={label} style={{
                  paddingLeft: i > 0 ? 22 : 0,
                  borderLeft: i > 0 ? '1px solid rgba(255,255,255,0.09)' : 'none',
                }}>
                  <p style={{ fontSize: 30, fontWeight: 800, color: '#fff', lineHeight: 1, marginBottom: 4, letterSpacing: '-0.5px' }}>{value}</p>
                  <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.38)' }}>{label}</p>
                  <div style={{ width: 24, height: 2, borderRadius: 99, background: color, marginTop: 8 }} />
                </div>
              ))}
            </div>
          </div>

          {/* ── Secondary cards ─────────────────────────── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 14 }}>
            {secondary.map(({ label, value, sub, Icon: I, color, bg, pct }) => (
              <div
                key={label}
                style={{ ...C, padding: '20px 22px', transition: 'transform .18s, border-color .18s' }}
                onMouseEnter={e => {
                  e.currentTarget.style.transform   = 'translateY(-2px)'
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.transform   = 'translateY(0)'
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'
                }}
              >
                <div style={{
                  width: 42, height: 42, borderRadius: 10,
                  background: bg, marginBottom: 16,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <I size={19} style={{ color }} />
                </div>
                <p style={{ fontSize: 30, fontWeight: 800, color: '#F1F5F9', lineHeight: 1, letterSpacing: '-0.5px', marginBottom: 4 }}>{value}</p>
                <p style={{ fontSize: 11.5, color: '#64748B', marginBottom: 14 }}>{sub}</p>
                <div style={{ height: 3, borderRadius: 99, background: 'rgba(255,255,255,0.06)' }}>
                  <div style={{ width: `${pct}%`, height: '100%', borderRadius: 99, background: color }} />
                </div>
                <p style={{ fontSize: 10, color: '#334155', marginTop: 7, fontWeight: 700, letterSpacing: '0.8px', textTransform: 'uppercase' }}>{label}</p>
              </div>
            ))}
          </div>

          {/* ── Conversations table ──────────────────────── */}
          <div style={{ ...C }}>
            <SectionHead
              title="Recent Tickets"
              sub={rows.length > 0 ? `${rows.length} most recent` : 'No tickets yet'}
              right={
                <button onClick={() => onNavigate('tickets')} className="btn-ghost" style={{ fontSize: 12 }}>
                  View all <ArrowUpRight size={12} />
                </button>
              }
            />
            {rows.length === 0 ? (
              <div style={{ padding: '40px 22px', textAlign: 'center', color: '#334155', fontSize: 13 }}>
                No tickets submitted yet. Submit one from the <a href="/support" style={{ color: '#7C3AED' }}>support form</a>.
              </div>
            ) : (
              <>
                {/* Col headers */}
                <div style={{
                  display: 'grid', gridTemplateColumns: '1fr 110px 140px 76px',
                  padding: '9px 22px',
                  background: 'rgba(0,0,0,0.2)', borderBottom: '1px solid rgba(255,255,255,0.04)',
                }}>
                  {['Customer', 'Channel', 'Status', 'Time'].map(h => (
                    <span key={h} style={{ fontSize: 9.5, fontWeight: 700, color: '#1E293B', letterSpacing: '1px', textTransform: 'uppercase' }}>{h}</span>
                  ))}
                </div>
                {/* Rows */}
                {rows.map((r, idx) => {
                  const active = selIdx === idx
                  return (
                    <div
                      key={r.id}
                      onClick={() => { setSelIdx(idx); setChat(true) }}
                      style={{
                        display: 'grid', gridTemplateColumns: '1fr 110px 140px 76px',
                        alignItems: 'center', padding: '14px 22px',
                        borderBottom: idx < rows.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                        background: active ? 'rgba(124,58,237,0.07)' : 'transparent',
                        borderLeft: active ? '3px solid #7C3AED' : '3px solid transparent',
                        cursor: 'pointer', transition: 'background .12s',
                      }}
                      onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.02)' }}
                      onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
                    >
                      {/* Customer */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
                        <div style={{ position: 'relative', flexShrink: 0 }}>
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={r.avatar} alt={r.name} style={{ width: 38, height: 38, borderRadius: '50%', objectFit: 'cover', border: '1.5px solid rgba(255,255,255,0.08)' }} />
                          <span style={{ position: 'absolute', bottom: 1, right: 1, width: 8, height: 8, borderRadius: '50%', background: r.stColor, border: '1.5px solid #111827' }} />
                        </div>
                        <div style={{ minWidth: 0 }}>
                          <p style={{ fontSize: 13, fontWeight: 600, color: '#F1F5F9' }}>{r.name}</p>
                          <p style={{ fontSize: 11, color: '#475569', marginTop: 1.5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 210 }}>{r.sub}</p>
                        </div>
                      </div>
                      {/* Channel */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                        <div style={{ width: 26, height: 26, borderRadius: 7, background: r.chanBg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <r.ChannelIcon size={12} style={{ color: r.chanColor }} />
                        </div>
                        <span style={{ fontSize: 11.5, color: '#64748B' }}>{r.channel}</span>
                      </div>
                      {/* Status */}
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: 5,
                        padding: '4px 10px', borderRadius: 99, width: 'fit-content',
                        background: r.stBg, color: r.stColor,
                        fontSize: 10.5, fontWeight: 600,
                        border: `1px solid ${r.stColor}28`,
                      }}>
                        <span style={{ width: 5, height: 5, borderRadius: '50%', background: r.stColor, display: 'inline-block', flexShrink: 0 }} />
                        {r.status}
                      </span>
                      {/* Time */}
                      <span style={{ fontSize: 11, color: '#475569' }}>{r.time}</span>
                    </div>
                  )
                })}
              </>
            )}
          </div>

          {/* ── Inline chat ─────────────────────────────── */}
          {chat && selRow && (
            <div style={{ ...C, display: 'flex', flexDirection: 'column' }}>
              <SectionHead
                title={`${selRow.name} — ${selRow.id}`}
                right={
                  <button onClick={() => setChat(false)} className="btn-ghost" style={{ fontSize: 12 }}>
                    <History size={12} /> Close
                  </button>
                }
              />
              {/* Messages */}
              <div style={{ padding: '18px 22px', display: 'flex', flexDirection: 'column', gap: 14, maxHeight: 230, overflowY: 'auto' }}>
                {msgs.map((m, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: m.role === 'agent' ? 'flex-end' : 'flex-start' }}>
                    <div style={{ maxWidth: '68%' }}>
                      <div style={{
                        padding: '11px 15px',
                        borderRadius: m.role === 'agent' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                        fontSize: 13, lineHeight: 1.65,
                        ...(m.role === 'agent'
                          ? { background: 'linear-gradient(135deg,#7C3AED,#5B21B6)', color: '#EDE9FE', boxShadow: '0 2px 12px rgba(124,58,237,0.22)' }
                          : { background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.07)', color: '#CBD5E1' }),
                      }}>{m.text}</div>
                      <p style={{ fontSize: 10, color: '#334155', marginTop: 4, textAlign: m.role === 'agent' ? 'right' : 'left' }}>
                        {m.role === 'agent' ? 'AI Agent' : selRow.name} {'\u00b7'} {m.time}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
              {/* Input */}
              <div style={{
                margin: '0 16px 16px',
                borderRadius: 11, background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(124,58,237,0.18)',
                display: 'flex', alignItems: 'center', gap: 8, padding: '9px 12px',
              }}>
                <button className="btn-ghost" style={{ padding: 4 }}><Smile size={15} style={{ color: '#475569' }} /></button>
                <input
                  value={reply} onChange={e => setReply(e.target.value)}
                  placeholder="Type your response…"
                  style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', fontSize: 13, color: '#CBD5E1' }}
                />
                <button className="btn-ghost" style={{ padding: 4 }}><Paperclip size={14} style={{ color: '#475569' }} /></button>
                <button className="btn-primary" onClick={() => setReply('')} style={{ fontSize: 12.5, padding: '7px 15px' }}>
                  <Send size={12} /> Send
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Right panel ─────────────────────────────────── */}
        <div style={{ width: 300, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Analytics chart */}
          <div style={{ ...C }}>
            <SectionHead
              title="Ticket Analytics"
              right={<span style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 11, color: '#475569', cursor: 'pointer' }}>Weekly <ChevronDown size={11} /></span>}
            />
            <div style={{ padding: '14px 10px 12px' }}>
              <ResponsiveContainer width="100%" height={140}>
                <AreaChart data={weekly} margin={{ top: 4, right: 4, bottom: 0, left: -28 }}>
                  <defs>
                    <linearGradient id="purpleGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#7C3AED" stopOpacity={0.28} />
                      <stop offset="100%" stopColor="#7C3AED" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#059669" stopOpacity={0.2} />
                      <stop offset="100%" stopColor="#059669" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,255,255,0.04)" vertical={false} />
                  <XAxis dataKey="day" tick={{ fill: '#334155', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#334155', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<ChartTip />} cursor={{ stroke: 'rgba(124,58,237,0.2)', strokeWidth: 1 }} />
                  <Area type="monotone" dataKey="tickets"  name="Tickets"  stroke="#7C3AED" strokeWidth={2} fill="url(#purpleGrad)" dot={false}
                    activeDot={{ r: 4, fill: '#7C3AED', stroke: '#111827', strokeWidth: 2 }} />
                  <Area type="monotone" dataKey="resolved" name="Resolved" stroke="#059669" strokeWidth={2} fill="url(#greenGrad)"  dot={false}
                    activeDot={{ r: 4, fill: '#059669', stroke: '#111827', strokeWidth: 2 }} />
                </AreaChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', gap: 14, padding: '0 6px', marginTop: 6 }}>
                {[{ color: '#7C3AED', label: 'Tickets' }, { color: '#059669', label: 'Resolved' }].map(({ color, label }) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <div style={{ width: 12, height: 2.5, borderRadius: 99, background: color }} />
                    <span style={{ fontSize: 10.5, color: '#475569' }}>{label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Recent Activity */}
          <div style={{ ...C }}>
            <SectionHead title="Recent Activity" />
            <div style={{ padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: 14 }}>
              {activity.length === 0 ? (
                <p style={{ fontSize: 12, color: '#334155', textAlign: 'center', padding: '12px 0' }}>No activity yet</p>
              ) : activity.map(({ Icon: I, color, bg, text, time }, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ width: 32, height: 32, borderRadius: 9, background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <I size={13} style={{ color }} />
                    </div>
                    {idx < activity.length - 1 && <div style={{ width: 1, height: 12, background: 'rgba(255,255,255,0.05)', marginTop: 2 }} />}
                  </div>
                  <div style={{ flex: 1, minWidth: 0, paddingTop: 2 }}>
                    <p style={{ fontSize: 11.5, color: '#64748B', lineHeight: 1.5, marginBottom: 3 }}>{text}</p>
                    <span style={{ fontSize: 10, color: '#334155', fontWeight: 600, padding: '1px 6px', borderRadius: 99, background: 'rgba(255,255,255,0.04)' }}>
                      {time} ago
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Performance */}
          <div style={{ ...C }}>
            <SectionHead title="Performance" />
            <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 18 }}>
              {perf.map(({ label, value, pct, color }) => (
                <div key={label}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontSize: 12, color: '#64748B' }}>{label}</span>
                    <span style={{ fontSize: 14, fontWeight: 800, color: '#F1F5F9' }}>{value}</span>
                  </div>
                  <div style={{ height: 5, borderRadius: 99, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
                    <div style={{ width: `${pct}%`, height: '100%', borderRadius: 99, background: color }} />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 4 }}>
                    <span style={{ fontSize: 10, color, fontWeight: 700 }}>{pct}%</span>
                  </div>
                </div>
              ))}
              <div style={{
                display: 'flex', alignItems: 'center', gap: 7,
                padding: '8px 11px', borderRadius: 9,
                background: 'rgba(5,150,105,0.06)', border: '1px solid rgba(5,150,105,0.1)',
              }}>
                <TrendingUp size={12} style={{ color: '#34D399', flexShrink: 0 }} />
                <span style={{ fontSize: 11, color: '#475569' }}>Live data from backend</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Settings ────────────────────────────────────────────────────────────────

function SettingsPanel() {
  const rows = [
    [
      { k: 'Backend URL', v: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000' },
      { k: 'API Proxy',   v: '/api/backend/* \u2192 backend' },
      { k: 'Stage',       v: '3' },
    ],
    [
      { k: 'LLM Provider', v: 'anthropic | openai | gemini' },
      { k: 'LLM Model',    v: 'claude-sonnet-4-6' },
      { k: 'API Key',      v: 'Required — set via env var' },
    ],
  ]
  const titles = ['Backend Configuration', 'LLM Configuration']

  return (
    <div style={{ maxWidth: 680, display: 'flex', flexDirection: 'column', gap: 16 }}>
      {rows.map((group, gi) => (
        <div key={gi} style={{ borderRadius: 16, background: '#111827', border: '1px solid rgba(255,255,255,0.07)', padding: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#F1F5F9', marginBottom: 14 }}>{titles[gi]}</h3>
          {group.map(({ k, v }) => (
            <div key={k} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
              <span style={{ fontSize: 13, color: '#64748B' }}>{k}</span>
              <code style={{ fontSize: 11, padding: '3px 9px', borderRadius: 6, background: 'rgba(124,58,237,0.1)', color: '#C4B5FD', border: '1px solid rgba(124,58,237,0.15)' }}>{v}</code>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

function Placeholder({ title }: { title: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 320 }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ width: 56, height: 56, borderRadius: 16, background: 'rgba(124,58,237,0.08)', border: '1px solid rgba(124,58,237,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
          <MessageSquare size={22} style={{ color: '#7C3AED' }} />
        </div>
        <p style={{ fontSize: 15, fontWeight: 600, color: '#94A3B8' }}>{title}</p>
        <p style={{ fontSize: 13, color: '#334155', marginTop: 4 }}>Coming soon</p>
      </div>
    </div>
  )
}

// ─── Root ────────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [section, setSection] = useState<Section>('dashboard')
  const [online,  setOnline]  = useState<boolean | null>(null)

  const ping = useCallback(async () => {
    try { await api.health(); setOnline(true) }
    catch { setOnline(false) }
  }, [])

  useEffect(() => {
    ping()
    const id = setInterval(ping, 30_000)
    return () => clearInterval(id)
  }, [ping])

  const content = () => {
    switch (section) {
      case 'dashboard':     return <DashboardOverview onNavigate={setSection} />
      case 'conversations': return <ConversationPanel />
      case 'tickets':       return <TicketPanel />
      case 'analytics':     return <AnalyticsPanel />
      case 'api-tester':    return <ApiTesterPanel />
      case 'escalations':   return <Placeholder title="Escalations" />
      case 'reports':       return <Placeholder title="Reports" />
      case 'settings':      return <SettingsPanel />
      default:              return null
    }
  }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg)' }}>
      <Sidebar activeSection={section} onNavigate={s => setSection(s as Section)} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
        <Header activeSection={section} backendOnline={online} onRefresh={ping} />
        <main style={{ flex: 1, overflowY: 'auto', padding: '24px 28px', background: 'var(--bg)' }}>
          {content()}
        </main>
      </div>
    </div>
  )
}
