'use client'

import { LayoutDashboard, Ticket, BarChart2, MessageSquare, AlertTriangle, FileText, Settings, Bot, Zap } from 'lucide-react'

interface SidebarProps {
  activeSection: string
  onNavigate: (section: string) => void
}

const navItems = [
  { id: 'dashboard',     label: 'Dashboard',     icon: LayoutDashboard },
  { id: 'conversations', label: 'Conversations',  icon: MessageSquare },
  { id: 'tickets',       label: 'Tickets',        icon: Ticket },
  { id: 'analytics',     label: 'Analytics',      icon: BarChart2 },
  { id: 'escalations',   label: 'Escalations',    icon: AlertTriangle },
  { id: 'reports',       label: 'Reports',        icon: FileText },
  { id: 'settings',      label: 'Settings',       icon: Settings },
]

export default function Sidebar({ activeSection, onNavigate }: SidebarProps) {
  return (
    <aside
      className="flex flex-col flex-shrink-0 overflow-hidden"
      style={{
        width: 'var(--sidebar-width)',
        background: '#0b0f17',
        borderRight: '1px solid rgba(255,255,255,0.06)',
        minHeight: '100vh',
      }}
    >
      {/* Logo */}
      <div className="px-5 pt-6 pb-5" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center text-white font-bold text-lg flex-shrink-0"
            style={{
              background: 'linear-gradient(135deg, #7c3aed 0%, #3b82f6 100%)',
              boxShadow: '0 0 16px rgba(139,92,246,0.4)',
            }}
          >
            N
          </div>
          <div>
            <span className="font-bold text-white text-base tracking-tight leading-tight">Nexora</span>
            <p className="text-xs text-gray-500 leading-tight mt-0.5">Customer Success FTE</p>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <span
            className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold"
            style={{ background: 'rgba(139,92,246,0.15)', color: '#a78bfa', border: '1px solid rgba(167,139,250,0.25)' }}
          >
            <Zap size={10} />
            Stage 3
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        <p className="text-xs font-semibold text-gray-600 uppercase tracking-widest px-3 mb-3">Main Menu</p>
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = activeSection === item.id
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={isActive ? 'nav-item-active' : 'nav-item-inactive'}
            >
              <Icon
                size={17}
                className={isActive ? 'text-violet-300' : 'text-gray-500'}
                style={isActive ? { filter: 'drop-shadow(0 0 6px rgba(167,139,250,0.6))' } : {}}
              />
              <span>{item.label}</span>
            </button>
          )
        })}
      </nav>

      {/* AI Robot widget */}
      <div className="px-3 pb-5 pt-2" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <div
          className="rounded-xl p-4"
          style={{
            background: 'linear-gradient(135deg, rgba(139,92,246,0.12) 0%, rgba(56,189,248,0.08) 100%)',
            border: '1px solid rgba(167,139,250,0.2)',
          }}
        >
          <div className="flex items-center gap-3 mb-2">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ background: 'rgba(139,92,246,0.25)', boxShadow: '0 0 10px rgba(139,92,246,0.3)' }}
            >
              <Bot size={16} className="text-violet-300" />
            </div>
            <div>
              <p className="text-sm font-semibold text-white leading-tight">AI Agent</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span
                  className="w-1.5 h-1.5 rounded-full bg-emerald-400"
                  style={{ boxShadow: '0 0 6px rgba(74,222,128,0.8)', animation: 'pulse 2s infinite' }}
                />
                <span className="text-xs text-emerald-400">Online</span>
              </div>
            </div>
          </div>
          <p className="text-xs text-gray-500">Powered by Claude AI</p>
          <p className="text-xs text-gray-600 mt-0.5">v3.0.0</p>
        </div>
      </div>
    </aside>
  )
}
