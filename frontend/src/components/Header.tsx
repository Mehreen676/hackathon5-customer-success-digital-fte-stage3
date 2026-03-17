'use client'

import { Bell, Search, RefreshCw, ChevronDown } from 'lucide-react'

interface Props {
  activeSection: string
  backendOnline: boolean | null
  onRefresh: () => void
}

const TITLES: Record<string, string> = {
  dashboard:     'Dashboard',
  tickets:       'Tickets',
  conversations: 'Conversations',
  analytics:     'Analytics',
  escalations:   'Escalations',
  reports:       'Reports',
  settings:      'Settings',
  'api-tester':  'API Tester',
}

const SUBTITLES: Record<string, string> = {
  dashboard:     'Overview of your customer success metrics',
  tickets:       'Manage and track all support tickets',
  conversations: 'Live customer interactions',
  analytics:     'Performance insights and trends',
  escalations:   'High-priority cases requiring attention',
  reports:       'Detailed performance reports',
  settings:      'Configure your workspace',
  'api-tester':  'Test the AI agent endpoints',
}

export default function Header({ activeSection, backendOnline, onRefresh }: Props) {
  const online  = backendOnline === true
  const pending = backendOnline === null
  const dotColor    = pending ? '#D97706' : online ? '#059669' : '#DC2626'
  const statusLabel = pending ? 'Connecting' : online ? 'Online' : 'Offline'

  return (
    <header style={{
      height: 'var(--header-h)',
      flexShrink: 0,
      background: 'var(--bg)',
      borderBottom: '1px solid var(--border)',
      display: 'flex', alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 28px',
      position: 'sticky', top: 0, zIndex: 40,
    }}>

      {/* Left: title */}
      <div>
        <h1 style={{ fontSize: 17, fontWeight: 800, color: '#F1F5F9', letterSpacing: '-0.3px', lineHeight: 1.2 }}>
          {TITLES[activeSection] ?? 'Dashboard'}
        </h1>
        <p style={{ fontSize: 11.5, color: 'var(--txt-4)', marginTop: 2 }}>
          {SUBTITLES[activeSection] ?? ''}
        </p>
      </div>

      {/* Right cluster */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>

        {/* Search */}
        <div style={{ position: 'relative' }}>
          <Search size={13} style={{ position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)', color: '#334155' }} />
          <input
            type="text"
            placeholder="Search…"
            style={{
              width: 210, height: 36,
              paddingLeft: 32, paddingRight: 14,
              borderRadius: 9,
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--border)',
              color: '#94A3B8', fontSize: 13, outline: 'none',
              transition: 'border-color .15s, box-shadow .15s',
            }}
            onFocus={e => {
              e.target.style.borderColor = 'rgba(124,58,237,0.45)'
              e.target.style.boxShadow   = '0 0 0 3px rgba(124,58,237,0.08)'
            }}
            onBlur={e => {
              e.target.style.borderColor = 'rgba(255,255,255,0.07)'
              e.target.style.boxShadow   = 'none'
            }}
          />
        </div>

        {/* Status pill */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '5px 11px', borderRadius: 99,
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid var(--border)',
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: dotColor, display: 'inline-block' }} />
          <span style={{ fontSize: 11.5, color: dotColor, fontWeight: 600 }}>{statusLabel}</span>
        </div>

        {/* Refresh */}
        <Btn onClick={onRefresh}><RefreshCw size={14} /></Btn>

        {/* Notifications */}
        <div style={{ position: 'relative' }}>
          <Btn><Bell size={14} /></Btn>
          <span style={{
            position: 'absolute', top: 7, right: 7,
            width: 6, height: 6, borderRadius: '50%',
            background: '#EC4899', border: '1.5px solid var(--bg)',
          }} />
        </div>

        <div style={{ width: 1, height: 22, background: 'var(--border)', margin: '0 2px' }} />

        {/* User */}
        <div
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '5px 10px 5px 5px', borderRadius: 10,
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid var(--border)',
            cursor: 'pointer', transition: 'all .15s',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = 'rgba(124,58,237,0.3)'
            e.currentTarget.style.background  = 'rgba(124,58,237,0.05)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'
            e.currentTarget.style.background  = 'rgba(255,255,255,0.03)'
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="https://i.pravatar.cc/150?img=47" alt="Mehreen"
            style={{ width: 28, height: 28, borderRadius: '50%', objectFit: 'cover', border: '2px solid rgba(124,58,237,0.4)' }}
          />
          <div>
            <p style={{ fontSize: 12.5, fontWeight: 700, color: '#E2E8F0', lineHeight: 1.2 }}>Mehreen A.</p>
            <p style={{ fontSize: 10, color: 'var(--txt-4)', lineHeight: 1 }}>Admin</p>
          </div>
          <ChevronDown size={11} style={{ color: '#334155' }} />
        </div>
      </div>
    </header>
  )
}

function Btn({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        width: 36, height: 36, borderRadius: 9,
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: 'var(--txt-4)', cursor: 'pointer', transition: 'all .15s',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.color        = '#94A3B8'
        e.currentTarget.style.borderColor  = 'rgba(124,58,237,0.3)'
        e.currentTarget.style.background   = 'rgba(124,58,237,0.06)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.color        = 'var(--txt-4)'
        e.currentTarget.style.borderColor  = 'rgba(255,255,255,0.07)'
        e.currentTarget.style.background   = 'rgba(255,255,255,0.03)'
      }}
    >{children}</button>
  )
}
