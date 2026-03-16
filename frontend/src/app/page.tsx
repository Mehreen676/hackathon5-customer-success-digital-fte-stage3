'use client'

import { useCallback, useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, Ticket, MessageSquare, AlertTriangle, CheckCircle, Clock, Activity } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import Sidebar from '@/components/Sidebar'
import Header from '@/components/Header'
import ConversationPanel from '@/components/ConversationPanel'
import TicketPanel from '@/components/TicketPanel'
import AnalyticsPanel from '@/components/AnalyticsPanel'
import ApiTesterPanel from '@/components/ApiTesterPanel'
import api from '@/lib/api'

type Section = 'dashboard' | 'conversations' | 'tickets' | 'analytics' | 'api-tester' | 'escalations' | 'reports' | 'settings'

// ─── Dashboard metric cards ────────────────────────────────
const STAT_CARDS = [
  { label: 'New Tickets',      value: '24',  delta: '+3',  up: true,  glowClass: 'card-glow-blue',   textColor: 'text-neon-blue',   Icon: Ticket },
  { label: 'Open Tickets',     value: '41',  delta: '+7',  up: true,  glowClass: 'card-glow-purple', textColor: 'text-neon-purple', Icon: MessageSquare },
  { label: 'Escalations',      value: '6',   delta: '-2',  up: false, glowClass: 'card-glow-pink',   textColor: 'text-neon-pink',   Icon: AlertTriangle },
  { label: 'Resolved Today',   value: '19',  delta: '+5',  up: true,  glowClass: 'card-glow-green',  textColor: 'text-neon-green',  Icon: CheckCircle },
]

// ─── Mini chart data ────────────────────────────────────────
const MINI_TREND = [
  { t: '9am',  v: 12 }, { t: '10am', v: 18 }, { t: '11am', v: 14 },
  { t: '12pm', v: 24 }, { t: '1pm',  v: 20 }, { t: '2pm',  v: 31 },
  { t: '3pm',  v: 27 }, { t: '4pm',  v: 19 },
]

// ─── Active conversations mock ──────────────────────────────
const ACTIVE_CONVS = [
  { id: 'C-001', name: 'Sarah Chen',    initials: 'SC', color: 'linear-gradient(135deg,#7c3aed,#3b82f6)', preview: 'Invoice from last month not found', channel: 'email',    chCls: 'badge-blue',   status: 'active',   statusCls: 'badge-green', time: '2m ago' },
  { id: 'C-002', name: 'James Liu',     initials: 'JL', color: 'linear-gradient(135deg,#059669,#0891b2)', preview: 'Urgent: need refund immediately',    channel: 'whatsapp', chCls: 'badge-green',  status: 'escalated', statusCls: 'badge-red',   time: '5m ago' },
  { id: 'C-003', name: 'Priya Sharma',  initials: 'PS', color: 'linear-gradient(135deg,#db2777,#7c3aed)', preview: 'SSO setup for enterprise account',    channel: 'web_form', chCls: 'badge-cyan',   status: 'resolved',  statusCls: 'badge-gray',  time: '1h ago' },
  { id: 'C-004', name: 'Ahmed Al-Farsi',initials: 'AA', color: 'linear-gradient(135deg,#dc2626,#9333ea)', preview: 'Legal complaint regarding billing',    channel: 'email',    chCls: 'badge-blue',   status: 'escalated', statusCls: 'badge-red',   time: '2h ago' },
  { id: 'C-005', name: 'Linda Wong',    initials: 'LW', color: 'linear-gradient(135deg,#0891b2,#059669)', preview: 'Slack OAuth integration failing',      channel: 'email',    chCls: 'badge-blue',   status: 'active',   statusCls: 'badge-green', time: '3h ago' },
]

// ─── Recent activity ────────────────────────────────────────
const RECENT_ACTIVITY = [
  { icon: '🎫', text: 'TKT-0048 escalated to billing team',        time: '2m ago',   color: '#f87171' },
  { icon: '✅', text: 'TKT-0047 auto-resolved via knowledge base',  time: '8m ago',   color: '#4ade80' },
  { icon: '🤖', text: 'LLM response generated for TKT-0046',        time: '15m ago',  color: '#a78bfa' },
  { icon: '📩', text: 'New Gmail webhook received from Sarah Chen',  time: '22m ago',  color: '#38bdf8' },
  { icon: '⚡', text: 'WhatsApp message processed in 124ms',         time: '34m ago',  color: '#22d3ee' },
  { icon: '🔔', text: 'TKT-0045 flagged for legal review',           time: '1h ago',   color: '#fb923c' },
]

// ─── Performance metrics ────────────────────────────────────
const PERF_METRICS = [
  { label: 'Avg Response Time',  value: '142ms', pct: 72, color: '#a78bfa' },
  { label: 'KB Hit Rate',        value: '68%',   pct: 68, color: '#38bdf8' },
  { label: 'AI Usage Rate',      value: '24%',   pct: 24, color: '#22d3ee' },
  { label: 'Resolution Rate',    value: '91%',   pct: 91, color: '#4ade80' },
]

const MiniTooltip = ({ active, payload }: { active?: boolean; payload?: { value: number }[] }) => {
  if (active && payload?.length) {
    return (
      <div className="px-2 py-1 rounded text-xs" style={{ background: '#1f2937', color: '#f1f5f9', border: '1px solid rgba(255,255,255,0.08)' }}>
        {payload[0].value}
      </div>
    )
  }
  return null
}

// ─── Main Dashboard overview ────────────────────────────────
function DashboardOverview({ onNavigate }: { onNavigate: (s: Section) => void }) {
  return (
    <div className="flex gap-5 h-full">
      {/* Center column */}
      <div className="flex-1 flex flex-col gap-5 min-w-0">
        {/* Stat cards */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
          {STAT_CARDS.map(({ label, value, delta, up, glowClass, textColor, Icon }) => (
            <div key={label} className={glowClass}>
              <div className="flex items-start justify-between mb-3">
                <p className="text-xs text-gray-500 font-medium">{label}</p>
                <Icon size={15} className="text-gray-600" />
              </div>
              <p className={`text-3xl font-bold ${textColor}`}>{value}</p>
              <div className="flex items-center gap-1 mt-2">
                {up ? <TrendingUp size={12} className="text-emerald-400" /> : <TrendingDown size={12} className="text-red-400" />}
                <span className={`text-xs font-medium ${up ? 'text-emerald-400' : 'text-red-400'}`}>{delta}</span>
                <span className="text-xs text-gray-600">today</span>
              </div>
            </div>
          ))}
        </div>

        {/* Active conversations table */}
        <div className="card-dark flex-1">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">Active Conversations</h3>
            <button onClick={() => onNavigate('conversations')} className="btn-ghost text-xs px-2 py-1">View all</button>
          </div>
          <table className="w-full">
            <thead>
              <tr>
                <th className="th-dark text-left">Customer</th>
                <th className="th-dark text-left">Preview</th>
                <th className="th-dark text-left">Channel</th>
                <th className="th-dark text-left">Status</th>
                <th className="th-dark text-left">Time</th>
              </tr>
            </thead>
            <tbody>
              {ACTIVE_CONVS.map((c) => (
                <tr
                  key={c.id}
                  className="cursor-pointer transition-all"
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <div
                        className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0"
                        style={{ background: c.color }}
                      >
                        {c.initials}
                      </div>
                      <span className="text-sm font-medium text-gray-200">{c.name}</span>
                    </div>
                  </td>
                  <td className="td-dark text-gray-500 max-w-[200px] truncate text-xs">{c.preview}</td>
                  <td className="td-dark"><span className={`badge-dark ${c.chCls} capitalize`}>{c.channel.replace('_', ' ')}</span></td>
                  <td className="td-dark"><span className={`badge-dark ${c.statusCls}`}>{c.status}</span></td>
                  <td className="td-dark text-xs text-gray-600">{c.time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Right panel */}
      <div className="flex flex-col gap-4" style={{ width: 300 }}>
        {/* Mini chart */}
        <div className="card-glow-purple">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Ticket Volume Today</h3>
            <Activity size={13} className="text-violet-400" />
          </div>
          <ResponsiveContainer width="100%" height={100}>
            <LineChart data={MINI_TREND} margin={{ top: 4, right: 4, bottom: 0, left: -30 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="t" tick={{ fill: '#4b5563', fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#4b5563', fontSize: 9 }} axisLine={false} tickLine={false} />
              <Tooltip content={<MiniTooltip />} />
              <Line
                type="monotone"
                dataKey="v"
                stroke="#a78bfa"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 3, fill: '#a78bfa' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Recent activity */}
        <div className="card-dark flex-1">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Recent Activity</h3>
            <Clock size={13} className="text-gray-600" />
          </div>
          <div className="space-y-3">
            {RECENT_ACTIVITY.map((item, i) => (
              <div key={i} className="flex items-start gap-2.5">
                <span className="text-sm flex-shrink-0 mt-0.5">{item.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-400 leading-snug">{item.text}</p>
                  <p className="text-[10px] text-gray-600 mt-0.5">{item.time}</p>
                </div>
                <div className="w-1 h-1 rounded-full flex-shrink-0 mt-1.5" style={{ backgroundColor: item.color, boxShadow: `0 0 4px ${item.color}` }} />
              </div>
            ))}
          </div>
        </div>

        {/* Performance metrics */}
        <div className="card-dark">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Performance</h3>
          <div className="space-y-3">
            {PERF_METRICS.map(({ label, value, pct, color }) => (
              <div key={label}>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs text-gray-500">{label}</span>
                  <span className="text-xs font-semibold" style={{ color }}>{value}</span>
                </div>
                <div className="rounded-full overflow-hidden" style={{ height: 4, background: 'rgba(255,255,255,0.06)' }}>
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${pct}%`, background: color, boxShadow: `0 0 6px ${color}66`, transition: 'width 0.6s ease' }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Settings panel ─────────────────────────────────────────
function SettingsPanel() {
  return (
    <div className="space-y-4 max-w-2xl">
      <div className="card-dark">
        <h3 className="text-sm font-semibold text-white mb-4">Backend Configuration</h3>
        <div className="space-y-2">
          {[
            { label: 'Backend URL',   value: 'http://localhost:8000' },
            { label: 'Frontend URL',  value: 'http://localhost:3000' },
            { label: 'API Proxy',     value: '/api/backend/* → backend' },
            { label: 'Stage',         value: '3' },
          ].map(({ label, value }) => (
            <div key={label} className="flex justify-between items-center py-2" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
              <span className="text-gray-500 text-sm">{label}</span>
              <code className="text-xs px-2 py-1 rounded" style={{ background: 'rgba(255,255,255,0.06)', color: '#a78bfa' }}>{value}</code>
            </div>
          ))}
        </div>
      </div>

      <div className="card-dark">
        <h3 className="text-sm font-semibold text-white mb-4">LLM Configuration</h3>
        <div className="space-y-2">
          {[
            { env: 'LLM_PROVIDER',      desc: 'anthropic | openai | gemini' },
            { env: 'LLM_MODEL',         desc: 'e.g. claude-sonnet-4-6' },
            { env: 'ANTHROPIC_API_KEY', desc: 'Required if provider=anthropic' },
            { env: 'OPENAI_API_KEY',    desc: 'Required if provider=openai' },
            { env: 'GEMINI_API_KEY',    desc: 'Required if provider=gemini' },
          ].map(({ env, desc }) => (
            <div key={env} className="flex justify-between items-center py-2" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
              <code className="text-xs px-2 py-1 rounded" style={{ background: 'rgba(167,139,250,0.12)', color: '#a78bfa' }}>{env}</code>
              <span className="text-gray-600 text-xs">{desc}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-600 mt-3">Set these in your <code className="text-violet-400">.env</code> file on the backend server.</p>
      </div>
    </div>
  )
}

function PlaceholderPanel({ title }: { title: string }) {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <p className="text-2xl mb-3">🚧</p>
        <p className="text-gray-400 font-medium">{title}</p>
        <p className="text-gray-600 text-sm mt-1">Coming soon</p>
      </div>
    </div>
  )
}

// ─── Root page ──────────────────────────────────────────────
export default function Dashboard() {
  const [activeSection, setActiveSection] = useState<Section>('dashboard')
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null)

  const checkHealth = useCallback(async () => {
    try {
      await api.health()
      setBackendOnline(true)
    } catch {
      setBackendOnline(false)
    }
  }, [])

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30_000)
    return () => clearInterval(interval)
  }, [checkHealth])

  const renderContent = () => {
    switch (activeSection) {
      case 'dashboard':     return <DashboardOverview onNavigate={setActiveSection} />
      case 'conversations': return <ConversationPanel />
      case 'tickets':       return <TicketPanel />
      case 'analytics':     return <AnalyticsPanel />
      case 'api-tester':    return <ApiTesterPanel />
      case 'escalations':   return <PlaceholderPanel title="Escalations" />
      case 'reports':       return <PlaceholderPanel title="Reports" />
      case 'settings':      return <SettingsPanel />
      default:              return null
    }
  }

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#05070d' }}>
      <Sidebar activeSection={activeSection} onNavigate={(s) => setActiveSection(s as Section)} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header
          activeSection={activeSection}
          backendOnline={backendOnline}
          onRefresh={checkHealth}
        />
        <main className="flex-1 overflow-y-auto p-5">
          {renderContent()}
        </main>
      </div>
    </div>
  )
}
