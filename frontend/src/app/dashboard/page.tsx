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
import api from '@/lib/api'

type Section =
  | 'dashboard' | 'conversations' | 'tickets' | 'analytics'
  | 'api-tester' | 'escalations'  | 'reports' | 'settings'

// ─── Data ────────────────────────────────────────────────────────────────────

const KPI = [
  { id: 'total',   label: 'Total Tickets',  value: '156', delta: '+12%', up: true,  Icon: Ticket,        color: '#7C3AED', bg: 'rgba(124,58,237,0.1)',  border: 'rgba(124,58,237,0.25)' },
  { id: 'open',    label: 'Open Tickets',   value: '17',  delta: '+5%',  up: true,  Icon: Inbox,         color: '#2563EB', bg: 'rgba(37,99,235,0.1)',    border: 'rgba(37,99,235,0.25)' },
  { id: 'done',    label: 'Resolved Today', value: '22',  delta: '+18%', up: true,  Icon: CheckCircle,   color: '#059669', bg: 'rgba(5,150,105,0.1)',    border: 'rgba(5,150,105,0.25)' },
  { id: 'esc',     label: 'Escalations',    value: '04',  delta: '+2%',  up: false, Icon: AlertTriangle, color: '#D97706', bg: 'rgba(217,119,6,0.1)',    border: 'rgba(217,119,6,0.25)' },
]

const WEEKLY = [
  { day: 'Mon', tickets: 38, resolved: 30 },
  { day: 'Tue', tickets: 52, resolved: 44 },
  { day: 'Wed', tickets: 45, resolved: 38 },
  { day: 'Thu', tickets: 68, resolved: 56 },
  { day: 'Fri', tickets: 55, resolved: 48 },
  { day: 'Sat', tickets: 35, resolved: 30 },
  { day: 'Sun', tickets: 48, resolved: 40 },
]

const SECONDARY = [
  { label: 'Avg Response', value: '1.2m', sub: 'per ticket',     Icon: Clock,   color: '#7C3AED', bg: 'rgba(124,58,237,0.08)', pct: 60 },
  { label: 'CSAT Score',   value: '4.8',  sub: 'out of 5.0',    Icon: Zap,     color: '#059669', bg: 'rgba(5,150,105,0.08)',   pct: 96 },
  { label: 'AI Handled',   value: '68%',  sub: 'of all tickets', Icon: Bot,     color: '#2563EB', bg: 'rgba(37,99,235,0.08)',   pct: 68 },
]

const ROWS = [
  {
    id: 'C-001', name: 'Sarah Lee',  email: 'sarah.lee@company.com',
    sub: 'Billing issue — invoice missing',
    avatar: 'https://i.pravatar.cc/150?img=5',
    ChannelIcon: Mail,          channel: 'Gmail',
    chanColor: '#7C3AED', chanBg: 'rgba(124,58,237,0.1)',
    status: 'In Progress', stColor: '#A855F7', stBg: 'rgba(124,58,237,0.1)',
    time: '2m ago',
  },
  {
    id: 'C-002', name: 'John Patel', email: 'john.patel@enterprise.io',
    sub: 'Connectivity issue on platform',
    avatar: 'https://i.pravatar.cc/150?img=12',
    ChannelIcon: MessageCircle, channel: 'WhatsApp',
    chanColor: '#059669', chanBg: 'rgba(5,150,105,0.1)',
    status: 'Pending',     stColor: '#D97706', stBg: 'rgba(217,119,6,0.1)',
    time: '5m ago',
  },
  {
    id: 'C-003', name: 'Lisa Wong',  email: 'lisa.wong@corp.com',
    sub: 'Password reset email not arriving',
    avatar: 'https://i.pravatar.cc/150?img=20',
    ChannelIcon: FileText,      channel: 'Web Form',
    chanColor: '#2563EB', chanBg: 'rgba(37,99,235,0.1)',
    status: 'Resolved',    stColor: '#059669', stBg: 'rgba(5,150,105,0.1)',
    time: '12m ago',
  },
  {
    id: 'C-004', name: 'Ahmed Khan', email: 'ahmed.khan@business.ae',
    sub: 'Product completely not working',
    avatar: 'https://i.pravatar.cc/150?img=33',
    ChannelIcon: Mail,          channel: 'Gmail',
    chanColor: '#7C3AED', chanBg: 'rgba(124,58,237,0.1)',
    status: 'Escalated',   stColor: '#DC2626', stBg: 'rgba(220,38,38,0.1)',
    time: '18m ago',
  },
]

const MESSAGES: Record<string, { role: 'agent'|'customer'; text: string; time: string }[]> = {
  'C-001': [
    { role: 'customer', text: 'Hi, I need help changing my billing details. The invoice from last month is missing.', time: '10:02 AM' },
    { role: 'agent',    text: 'Hi Sarah! You can update billing info under Settings \u2192 Billing. I can also pull the missing invoice directly \u2014 let me check.', time: '10:03 AM' },
    { role: 'customer', text: 'That would be great, thanks!', time: '10:04 AM' },
  ],
  'C-002': [
    { role: 'customer', text: 'I am facing connectivity issues with the platform since this morning.', time: '10:18 AM' },
    { role: 'agent',    text: "Hi John! I've checked your account \u2014 there's a routing issue. Our team is on it. ETA: 30 minutes.", time: '10:18 AM' },
  ],
  'C-003': [
    { role: 'customer', text: "I can't reset my password. The reset email is not arriving.", time: '09:51 AM' },
    { role: 'agent',    text: "Hi Lisa! Please check your spam folder. If it isn't there I can manually reset your account right now.", time: '09:52 AM' },
    { role: 'customer', text: 'Found it in spam. All sorted now, thanks!', time: '09:54 AM' },
  ],
  'C-004': [
    { role: 'customer', text: 'The product is completely not working! This is very urgent for our team.', time: '09:35 AM' },
    { role: 'agent',    text: "Hi Ahmed! I've escalated this to our technical team as high priority. You'll receive a callback within the hour. Ref: TKT-0045.", time: '09:36 AM' },
  ],
}

const ACTIVITY = [
  { Icon: Bot,           color: '#7C3AED', bg: 'rgba(124,58,237,0.1)', text: 'AI resolved billing issue for Sarah Lee', time: '2m' },
  { Icon: Plus,          color: '#2563EB', bg: 'rgba(37,99,235,0.1)',   text: 'Ticket #TKT-0048 auto-created via Gmail',  time: '6m' },
  { Icon: AlertTriangle, color: '#D97706', bg: 'rgba(217,119,6,0.1)',   text: 'Ahmed Khan escalated to senior agent',     time: '15m' },
  { Icon: CheckCircle,   color: '#059669', bg: 'rgba(5,150,105,0.1)',   text: 'Lisa Wong issue resolved automatically',   time: '22m' },
  { Icon: User,          color: '#A855F7', bg: 'rgba(168,85,247,0.1)',  text: 'New VIP customer John Patel onboarded',    time: '31m' },
]

const PERF = [
  { label: 'Avg Response', value: '1.2 min', pct: 60, color: '#7C3AED' },
  { label: 'CSAT Score',   value: '4.8 / 5', pct: 96, color: '#059669' },
  { label: 'Resolution',   value: '92%',     pct: 92, color: '#2563EB' },
]

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

function KPICard({ label, value, delta, up, Icon, color, bg, border }: typeof KPI[0]) {
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
      {/* Top row */}
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
          background: up ? 'rgba(5,150,105,0.08)' : 'rgba(220,38,38,0.08)',
          border: `1px solid ${up ? 'rgba(5,150,105,0.2)' : 'rgba(220,38,38,0.2)'}`,
          color: up ? '#34D399' : '#F87171',
          fontSize: 11, fontWeight: 600,
        }}>
          {up ? '↑' : '↓'} {delta}
        </span>
      </div>
      {/* Value */}
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
  const [selRow, setSelRow] = useState(ROWS[0])
  const [reply,  setReply]  = useState('')
  const [chat,   setChat]   = useState(true)
  const msgs = MESSAGES[selRow.id] ?? []

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
        {KPI.map(k => <KPICard key={k.id} {...k} />)}
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
                <p style={{ fontSize: 60, fontWeight: 900, color: '#fff', lineHeight: 1, letterSpacing: '-2.5px', marginBottom: 6 }}>92%</p>
                <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.42)', marginBottom: 20 }}>Resolution Rate this week</p>
                <div style={{
                  display: 'inline-flex', alignItems: 'center', gap: 7,
                  padding: '6px 14px', borderRadius: 99,
                  background: 'rgba(255,255,255,0.08)',
                  border: '1px solid rgba(255,255,255,0.12)',
                }}>
                  <TrendingUp size={13} style={{ color: '#4ADE80' }} />
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#4ADE80' }}>+12%</span>
                  <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>vs last week</span>
                </div>
              </div>
              {/* Mini chart */}
              <div style={{ width: 210, height: 96, opacity: 0.85, flexShrink: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={WEEKLY} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
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
                { label: 'Resolved',    value: '22', color: '#4ADE80' },
                { label: 'In Progress', value: '17', color: '#FACC15' },
                { label: 'Escalated',   value: '04', color: '#F87171' },
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
            {SECONDARY.map(({ label, value, sub, Icon: I, color, bg, pct }) => (
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
              title="Active Conversations"
              sub="4 live interactions"
              right={
                <button onClick={() => onNavigate('conversations')} className="btn-ghost" style={{ fontSize: 12 }}>
                  View all <ArrowUpRight size={12} />
                </button>
              }
            />
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
            {ROWS.map((r, idx) => {
              const active = selRow.id === r.id
              return (
                <div
                  key={r.id}
                  onClick={() => { setSelRow(r); setChat(true) }}
                  style={{
                    display: 'grid', gridTemplateColumns: '1fr 110px 140px 76px',
                    alignItems: 'center', padding: '14px 22px',
                    borderBottom: idx < ROWS.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
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
          </div>

          {/* ── Inline chat ─────────────────────────────── */}
          {chat && (
            <div style={{ ...C, display: 'flex', flexDirection: 'column' }}>
              <SectionHead
                title={`${selRow.name} — ${selRow.email}`}
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
                <AreaChart data={WEEKLY} margin={{ top: 4, right: 4, bottom: 0, left: -28 }}>
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
              {ACTIVITY.map(({ Icon: I, color, bg, text, time }, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ width: 32, height: 32, borderRadius: 9, background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <I size={13} style={{ color }} />
                    </div>
                    {idx < ACTIVITY.length - 1 && <div style={{ width: 1, height: 12, background: 'rgba(255,255,255,0.05)', marginTop: 2 }} />}
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
              {PERF.map(({ label, value, pct, color }) => (
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
                <span style={{ fontSize: 11, color: '#475569' }}>All metrics up vs last week</span>
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
