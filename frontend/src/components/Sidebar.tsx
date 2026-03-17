'use client'

import {
  LayoutDashboard, Ticket, MessageSquare, BarChart2,
  AlertTriangle, FileText, Settings, Zap, ChevronRight,
} from 'lucide-react'

interface Props {
  activeSection: string
  onNavigate: (s: string) => void
}

const NAV = [
  { id: 'dashboard',     label: 'Dashboard',    icon: LayoutDashboard },
  { id: 'tickets',       label: 'Tickets',       icon: Ticket,         badge: null },
  { id: 'conversations', label: 'Conversations', icon: MessageSquare,  badge: 4 },
  { id: 'analytics',     label: 'Analytics',     icon: BarChart2,      badge: null },
  { id: 'escalations',   label: 'Escalations',   icon: AlertTriangle,  badge: 2, red: true },
  { id: 'reports',       label: 'Reports',       icon: FileText,       badge: null },
  { id: 'settings',      label: 'Settings',      icon: Settings,       badge: null },
]

export default function Sidebar({ activeSection, onNavigate }: Props) {
  return (
    <aside style={{
      width: 'var(--sidebar-w)',
      minHeight: '100vh',
      flexShrink: 0,
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--surface)',
      borderRight: '1px solid var(--border)',
    }}>

      {/* ── Brand ─────────────────────────────────────────── */}
      <div style={{ padding: '24px 20px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 11, flexShrink: 0,
            background: 'linear-gradient(135deg, #7C3AED, #A855F7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(124,58,237,0.4)',
          }}>
            <Zap size={19} color="#fff" />
          </div>
          <div>
            <p style={{ fontSize: 16, fontWeight: 800, color: '#F1F5F9', letterSpacing: '-0.3px' }}>
              Nexora
            </p>
            <p style={{ fontSize: 11, color: 'var(--txt-4)', marginTop: 1 }}>
              Customer Success FTE
            </p>
          </div>
        </div>

        {/* Pills */}
        <div style={{ display: 'flex', gap: 6 }}>
          <span style={{
            padding: '3px 9px', borderRadius: 99,
            fontSize: 10, fontWeight: 700, letterSpacing: '0.6px', textTransform: 'uppercase',
            background: 'rgba(124,58,237,0.1)', color: '#C4B5FD',
            border: '1px solid rgba(124,58,237,0.2)',
          }}>Stage 3</span>
          <span style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '3px 9px', borderRadius: 99,
            fontSize: 10, fontWeight: 700, letterSpacing: '0.6px', textTransform: 'uppercase',
            background: 'rgba(5,150,105,0.1)', color: '#34D399',
            border: '1px solid rgba(5,150,105,0.18)',
          }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#34D399', display: 'inline-block' }} />
            Live
          </span>
        </div>
      </div>

      {/* ── Nav ───────────────────────────────────────────── */}
      <nav style={{ flex: 1, padding: '4px 12px', overflowY: 'auto' }}>
        <p style={{
          fontSize: 9.5, fontWeight: 700, color: '#1E293B',
          letterSpacing: '1.4px', textTransform: 'uppercase',
          padding: '0 8px 10px',
        }}>Main Menu</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {NAV.map(({ id, label, icon: Icon, badge, red }) => {
            const active = activeSection === id
            return (
              <button
                key={id}
                onClick={() => onNavigate(id)}
                className={active ? 'nav-active' : 'nav-inactive'}
              >
                <div style={{
                  width: 34, height: 34, borderRadius: 9, flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: active ? 'rgba(124,58,237,0.2)' : 'rgba(255,255,255,0.04)',
                  transition: 'background .15s',
                }}>
                  <Icon size={16} style={{ color: active ? '#C4B5FD' : '#475569', transition: 'color .15s' }} />
                </div>

                <span style={{ flex: 1, fontSize: 13.5, fontWeight: active ? 600 : 500 }}>{label}</span>

                {badge ? (
                  <span style={{
                    minWidth: 18, height: 18, borderRadius: 99,
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 10, fontWeight: 700, padding: '0 5px',
                    background: red ? 'rgba(220,38,38,0.12)' : 'rgba(124,58,237,0.12)',
                    color: red ? '#FCA5A5' : '#C4B5FD',
                    border: `1px solid ${red ? 'rgba(220,38,38,0.25)' : 'rgba(124,58,237,0.2)'}`,
                  }}>{badge}</span>
                ) : null}

                {active && <ChevronRight size={12} style={{ color: '#7C3AED', flexShrink: 0 }} />}
              </button>
            )
          })}
        </div>
      </nav>

      {/* ── User ──────────────────────────────────────────── */}
      <div style={{
        padding: '16px 20px',
        borderTop: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="https://i.pravatar.cc/150?img=47"
          alt="Mehreen"
          style={{
            width: 36, height: 36, borderRadius: '50%',
            objectFit: 'cover', flexShrink: 0,
            border: '2px solid rgba(124,58,237,0.45)',
          }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontSize: 13, fontWeight: 700, color: '#E2E8F0', lineHeight: 1.2 }}>Mehreen A.</p>
          <p style={{ fontSize: 11, color: 'var(--txt-4)', marginTop: 1 }}>Admin</p>
        </div>
        <Settings size={13} style={{ color: '#334155', cursor: 'pointer', flexShrink: 0 }} />
      </div>
    </aside>
  )
}
