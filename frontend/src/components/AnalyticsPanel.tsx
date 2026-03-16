'use client'

import { useEffect, useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import api from '@/lib/api'

interface AnalyticsSummary {
  total_interactions: number
  avg_response_time_ms: number
  escalation_rate: number
  kb_hit_rate: number
  ai_usage_rate: number
  fallback_rate: number
  ticket_creation_rate: number
  interactions_by_channel: Record<string, number>
  interactions_by_intent: Record<string, number>
  interactions_by_source: Record<string, number>
  total_tokens_used: number
  source?: string
}

// Static trend data for the line chart
const TREND_DATA = [
  { day: 'Mon', tickets: 38, escalations: 4 },
  { day: 'Tue', tickets: 52, escalations: 7 },
  { day: 'Wed', tickets: 45, escalations: 5 },
  { day: 'Thu', tickets: 61, escalations: 9 },
  { day: 'Fri', tickets: 48, escalations: 6 },
  { day: 'Sat', tickets: 29, escalations: 2 },
  { day: 'Sun', tickets: 35, escalations: 3 },
]

function GlowCard({ label, value, sub, glowClass, textColor }: { label: string; value: string; sub?: string; glowClass: string; textColor: string }) {
  return (
    <div className={glowClass}>
      <p className="text-xs text-gray-500 font-medium mb-1">{label}</p>
      <p className={`text-3xl font-bold ${textColor}`}>{value}</p>
      {sub && <p className="text-xs text-gray-600 mt-1">{sub}</p>}
    </div>
  )
}

function DarkBarChart({ data, title }: { data: Record<string, number>; title: string }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1])
  const max = Math.max(...entries.map(([, v]) => v), 1)
  const barColors = ['#a78bfa', '#38bdf8', '#4ade80', '#fb923c', '#f472b6', '#22d3ee']

  return (
    <div className="card-dark">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h3>
      <div className="space-y-3">
        {entries.map(([key, val], i) => (
          <div key={key} className="flex items-center gap-3">
            <span className="text-xs text-gray-500 w-24 truncate capitalize">{key.replace(/_/g, ' ')}</span>
            <div className="flex-1 rounded-full overflow-hidden" style={{ height: 6, background: 'rgba(255,255,255,0.06)' }}>
              <div
                className="h-full rounded-full"
                style={{
                  width: `${(val / max) * 100}%`,
                  background: barColors[i % barColors.length],
                  boxShadow: `0 0 6px ${barColors[i % barColors.length]}66`,
                  transition: 'width 0.6s ease',
                }}
              />
            </div>
            <span className="text-xs font-semibold text-gray-300 w-8 text-right">{val}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: { color: string; name: string; value: number }[]; label?: string }) => {
  if (active && payload && payload.length) {
    return (
      <div
        className="px-3 py-2 rounded-lg text-xs"
        style={{ background: '#1f2937', border: '1px solid rgba(255,255,255,0.1)', color: '#f1f5f9' }}
      >
        <p className="font-semibold mb-1 text-gray-300">{label}</p>
        {payload.map((p) => (
          <p key={p.name} style={{ color: p.color }}>
            {p.name}: <span className="font-bold">{p.value}</span>
          </p>
        ))}
      </div>
    )
  }
  return null
}

export default function AnalyticsPanel() {
  const [data, setData] = useState<AnalyticsSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getAnalyticsSummary().then((d) => {
      setData(d as AnalyticsSummary)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-3 text-gray-500">
          <div className="w-4 h-4 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
          Loading analytics…
        </div>
      </div>
    )
  }

  if (!data) {
    return <div className="card-dark text-gray-500 text-sm">Failed to load analytics data.</div>
  }

  return (
    <div className="space-y-5">
      {data.source === 'demo' && (
        <div
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm"
          style={{ background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)', color: '#fbbf24' }}
        >
          <span>📊</span>
          <span>Showing demo data — start the backend and process messages to see live metrics.</span>
        </div>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <GlowCard label="Total Interactions" value={data.total_interactions.toLocaleString()} sub="All time" glowClass="card-glow-purple" textColor="text-neon-purple" />
        <GlowCard label="Avg Response Time" value={`${Math.round(data.avg_response_time_ms)} ms`} sub="End-to-end" glowClass="card-glow-blue" textColor="text-neon-blue" />
        <GlowCard label="KB Hit Rate" value={`${Math.round(data.kb_hit_rate * 100)}%`} sub="Knowledge base" glowClass="card-glow-green" textColor="text-neon-green" />
        <GlowCard label="AI Usage Rate" value={`${Math.round(data.ai_usage_rate * 100)}%`} sub="LLM invoked" glowClass="card-glow-cyan" textColor="text-neon-cyan" />
      </div>

      {/* Secondary KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <GlowCard label="Escalation Rate" value={`${Math.round(data.escalation_rate * 100)}%`} glowClass="card-dark border border-red-500/20" textColor="text-red-400" />
        <GlowCard label="Ticket Creation" value={`${Math.round(data.ticket_creation_rate * 100)}%`} glowClass="card-dark border border-sky-500/20" textColor="text-sky-400" />
        <GlowCard label="Total Tokens" value={data.total_tokens_used.toLocaleString()} sub="LLM tokens" glowClass="card-dark border border-violet-500/20" textColor="text-violet-400" />
      </div>

      {/* Line chart */}
      <div className="card-glow-purple">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Weekly Trend — Tickets &amp; Escalations</h3>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={TREND_DATA} margin={{ top: 5, right: 10, bottom: 5, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="day" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12, color: '#9ca3af' }} />
            <Line
              type="monotone"
              dataKey="tickets"
              stroke="#a78bfa"
              strokeWidth={2}
              dot={{ fill: '#a78bfa', r: 3, strokeWidth: 0 }}
              activeDot={{ r: 5, fill: '#a78bfa', boxShadow: '0 0 8px #a78bfa' }}
            />
            <Line
              type="monotone"
              dataKey="escalations"
              stroke="#f472b6"
              strokeWidth={2}
              dot={{ fill: '#f472b6', r: 3, strokeWidth: 0 }}
              activeDot={{ r: 5, fill: '#f472b6' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Bar charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <DarkBarChart title="Interactions by Channel" data={data.interactions_by_channel} />
        <DarkBarChart title="Interactions by Intent" data={data.interactions_by_intent} />
        <div className="card-dark">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Response Source Distribution</h3>
          <div className="space-y-3">
            {Object.entries(data.interactions_by_source).map(([key, val]) => {
              const total = Object.values(data.interactions_by_source).reduce((a, b) => a + b, 0)
              const pct = Math.round((val / total) * 100)
              const colors: Record<string, string> = { kb: '#a78bfa', llm: '#38bdf8', fallback: '#fbbf24', escalation: '#f87171' }
              const color = colors[key] || '#94a3b8'
              return (
                <div key={key} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}` }} />
                    <span className="capitalize text-gray-400 text-xs">{key}</span>
                  </div>
                  <span className="text-xs font-semibold text-gray-300">{val} <span className="text-gray-600">({pct}%)</span></span>
                </div>
              )
            })}
          </div>
          <div className="mt-4 flex h-2 rounded-full overflow-hidden gap-px">
            {Object.entries(data.interactions_by_source).map(([key, val]) => {
              const total = Object.values(data.interactions_by_source).reduce((a, b) => a + b, 0)
              const colors: Record<string, string> = { kb: '#a78bfa', llm: '#38bdf8', fallback: '#fbbf24', escalation: '#f87171' }
              return (
                <div
                  key={key}
                  style={{ width: `${(val / total) * 100}%`, backgroundColor: colors[key] || '#94a3b8' }}
                  title={`${key}: ${val}`}
                />
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
