'use client'

import { Bell, Search, RefreshCw } from 'lucide-react'

interface HeaderProps {
  activeSection: string
  backendOnline: boolean | null
  onRefresh: () => void
}

export default function Header({ backendOnline, onRefresh }: HeaderProps) {
  const statusColor =
    backendOnline === null ? '#fbbf24' :
    backendOnline          ? '#4ade80'  : '#f87171'

  const statusText =
    backendOnline === null ? 'Connecting…' :
    backendOnline          ? 'Backend Online' : 'Backend Offline'

  return (
    <header
      className="flex items-center justify-between px-6 flex-shrink-0 sticky top-0 z-20"
      style={{
        height: 'var(--header-height)',
        background: 'rgba(11,15,23,0.85)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      {/* Title */}
      <div className="flex items-center gap-4">
        <div>
          <h1 className="text-base font-semibold text-white tracking-tight">Customer Support AI Dashboard</h1>
          <p className="text-xs text-gray-500">Nexora · Stage 3 System</p>
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Search */}
        <div className="relative hidden sm:block">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="Search tickets, customers…"
            className="input-dark pl-8 py-1.5 text-xs w-52"
          />
        </div>

        {/* Backend status */}
        <div
          className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium"
          style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: statusColor, boxShadow: `0 0 6px ${statusColor}` }}
          />
          <span style={{ color: statusColor }}>{statusText}</span>
        </div>

        {/* Refresh */}
        <button
          onClick={onRefresh}
          className="btn-ghost p-2"
          title="Refresh"
        >
          <RefreshCw size={15} />
        </button>

        {/* Notifications */}
        <button className="relative btn-ghost p-2" title="Notifications">
          <Bell size={15} />
          <span
            className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full"
            style={{ background: '#f472b6', boxShadow: '0 0 6px rgba(244,114,182,0.8)' }}
          />
        </button>

        {/* User avatar */}
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold text-white flex-shrink-0 cursor-pointer avatar-ring"
          style={{ background: 'linear-gradient(135deg, #7c3aed 0%, #3b82f6 100%)' }}
        >
          M
        </div>
      </div>
    </header>
  )
}
