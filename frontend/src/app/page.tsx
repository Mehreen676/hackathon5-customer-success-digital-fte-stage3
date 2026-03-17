'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  Zap, PenLine, Search, LayoutDashboard,
  Ticket, BookOpen, AlertTriangle, Globe,
  ArrowRight, Sun, Moon, CheckCircle,
} from 'lucide-react'

// ─────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────
type Card = {
  icon: React.ElementType
  color: string
  title: string
  description: string
  label: string
  href: string
}

type Stat = {
  icon: React.ElementType
  value: string
  label: string
  color: string
}

// ─────────────────────────────────────────────────────────────────
// DATA
// ─────────────────────────────────────────────────────────────────
const CARDS: Card[] = [
  {
    icon: PenLine,
    color: '#7C3AED',
    title: 'Submit a Request',
    description:
      'Send a message about any billing, account, or technical issue. Our AI agent picks it up instantly and responds within seconds.',
    label: 'Get Help',
    href: '/support',
  },
  {
    icon: Search,
    color: '#2563EB',
    title: 'Track Your Ticket',
    description:
      'Already submitted? Enter your ticket reference to see real-time status, priority level, and the latest response from our team.',
    label: 'Track Now',
    href: '/track-ticket',
  },
  {
    icon: LayoutDashboard,
    color: '#059669',
    title: 'Admin Dashboard',
    description:
      'Internal view for agents. Monitor live conversations, manage open tickets, and review AI performance across all channels.',
    label: 'Open Dashboard',
    href: '/dashboard',
  },
]

const STATS: Stat[] = [
  { icon: Ticket,        value: '1,247+', label: 'Tickets Analyzed',       color: '#7C3AED' },
  { icon: BookOpen,      value: '320+',   label: 'Knowledge Base Entries', color: '#2563EB' },
  { icon: AlertTriangle, value: '<2%',    label: 'Escalation Rate',        color: '#D97706' },
  { icon: Globe,         value: '3',      label: 'Channels Supported',     color: '#059669' },
]

// ─────────────────────────────────────────────────────────────────
// NAV LINK
// ─────────────────────────────────────────────────────────────────
function NavLink({ label, href }: { label: string; href: string }) {
  return (
    <Link
      href={href}
      style={{
        padding: '9px 22px',
        borderRadius: 9,
        fontSize: 16,
        fontWeight: 600,
        color: '#CBD5E1',
        textDecoration: 'none',
        transition: 'color 0.15s, background 0.15s',
        letterSpacing: '-0.1px',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.color = '#F1F5F9'
        e.currentTarget.style.background = 'rgba(255,255,255,0.06)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.color = '#94A3B8'
        e.currentTarget.style.background = 'transparent'
      }}
    >
      {label}
    </Link>
  )
}

// ─────────────────────────────────────────────────────────────────
// PAGE
// ─────────────────────────────────────────────────────────────────
export default function LandingPage() {
  const [atTop, setAtTop]   = useState(true)
  const [isDark, setIsDark] = useState(true)

  useEffect(() => {
    const fn = () => setAtTop(window.scrollY < 20)
    window.addEventListener('scroll', fn, { passive: true })
    return () => window.removeEventListener('scroll', fn)
  }, [])

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0B0F19',
      color: '#E2E8F0',
      fontFamily: 'Inter, system-ui, sans-serif',
      overflowX: 'hidden',
    }}>

      {/* ─── NAVBAR ──────────────────────────────────────────────── */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 100,
        height: 68,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 56px',
        background: atTop ? 'rgba(11,15,25,0.6)' : 'rgba(11,15,25,0.95)',
        backdropFilter: 'blur(18px)',
        WebkitBackdropFilter: 'blur(18px)',
        borderBottom: atTop ? '1px solid transparent' : '1px solid rgba(255,255,255,0.07)',
        transition: 'background 0.3s, border-color 0.3s',
      }}>

        {/* Logo */}
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 11, textDecoration: 'none' }}>
          <div style={{
            width: 38, height: 38, borderRadius: 10,
            background: 'linear-gradient(135deg,#7C3AED,#A855F7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 2px 12px rgba(124,58,237,0.3)',
          }}>
            <Zap size={18} color="#fff" />
          </div>
          <span style={{ fontSize: 18, fontWeight: 800, color: '#F1F5F9', letterSpacing: '-0.4px' }}>
            Nexora
          </span>
        </Link>

        {/* Center links */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <NavLink label="Submit Request" href="/support" />
          <NavLink label="Track Ticket"   href="/track-ticket" />
          <NavLink label="Dashboard"      href="/dashboard" />
        </div>

        {/* Right: toggle */}
        <button
          onClick={() => setIsDark(v => !v)}
          aria-label="Toggle theme"
          style={{
            width: 40, height: 40, borderRadius: 10,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.09)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#64748B', cursor: 'pointer',
            transition: 'all 0.15s',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = 'rgba(124,58,237,0.12)'
            e.currentTarget.style.borderColor = 'rgba(124,58,237,0.35)'
            e.currentTarget.style.color = '#C4B5FD'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
            e.currentTarget.style.borderColor = 'rgba(255,255,255,0.09)'
            e.currentTarget.style.color = '#64748B'
          }}
        >
          {isDark ? <Moon size={16} /> : <Sun size={16} />}
        </button>
      </nav>

      {/* ─── HERO ────────────────────────────────────────────────── */}
      <section style={{
        position: 'relative',
        padding: '64px 24px 96px',
        overflow: 'hidden',
      }}>

        {/* Glow — pinned to section center */}
        <div style={{
          position: 'absolute', top: 0, left: '50%',
          transform: 'translateX(-50%)',
          width: 1100, height: 640,
          borderRadius: '50%',
          background: 'radial-gradient(ellipse at 50% 40%, rgba(124,58,237,0.1) 0%, transparent 62%)',
          pointerEvents: 'none',
        }} />

        {/*
          Single centered column — all children share one axis.
          alignItems: center locks every element to the same horizontal midpoint.
        */}
        <div style={{
          position: 'relative',
          maxWidth: 900,
          margin: '0 auto',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
        }}>

          {/* Eyebrow badge */}
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 9,
            padding: '7px 20px', borderRadius: 99,
            background: 'rgba(124,58,237,0.1)',
            border: '1px solid rgba(124,58,237,0.24)',
            fontSize: 13, fontWeight: 600, color: '#C4B5FD',
            marginBottom: 28, letterSpacing: '0.3px',
          }}>
            <span style={{
              width: 7, height: 7, borderRadius: '50%',
              background: '#A855F7', display: 'inline-block',
            }} />
            Stage 3 &nbsp;·&nbsp; Multi-Provider AI &nbsp;·&nbsp; Real-Time Support
          </div>

          {/* Headline — fills full container width so text wraps centered */}
          <h1 style={{
            width: '100%',
            fontSize: 'clamp(40px, 6.5vw, 72px)',
            fontWeight: 900,
            lineHeight: 1.08,
            letterSpacing: '-2px',
            color: '#F1F5F9',
            marginBottom: 24,
          }}>
            AI-Powered{' '}
            <span style={{
              background: 'linear-gradient(120deg,#A855F7 0%,#7C3AED 45%,#3B82F6 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}>
              Customer Support
            </span>
            {' '}at Scale
          </h1>

          {/* Subtitle — narrower than headline for optical balance */}
          <p style={{
            maxWidth: 580,
            fontSize: 'clamp(15px, 1.7vw, 18px)',
            color: '#94A3B8',
            lineHeight: 1.8,
            marginBottom: 44,
          }}>
            Nexora&apos;s Digital FTE handles inbound support across Email, WhatsApp, and
            Web Form — powered by Claude, GPT-4o &amp; Gemini — with automatic ticket
            creation and smart escalation detection.
          </p>

          {/* CTA buttons */}
          <div style={{
            display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap',
            marginBottom: 52,
          }}>
            <Link
              href="/support"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 9,
                padding: '15px 32px', borderRadius: 11,
                background: 'linear-gradient(135deg,#7C3AED,#6D28D9)',
                color: '#fff', fontWeight: 700, fontSize: 16,
                textDecoration: 'none',
                boxShadow: '0 4px 24px rgba(124,58,237,0.32)',
                transition: 'transform 0.2s, box-shadow 0.2s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 10px 36px rgba(124,58,237,0.42)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = '0 4px 24px rgba(124,58,237,0.32)'
              }}
            >
              Submit a Request <ArrowRight size={17} />
            </Link>
            <Link
              href="/dashboard"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 9,
                padding: '15px 32px', borderRadius: 11,
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.12)',
                color: '#94A3B8', fontWeight: 600, fontSize: 16,
                textDecoration: 'none',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'rgba(124,58,237,0.4)'
                e.currentTarget.style.color = '#F1F5F9'
                e.currentTarget.style.background = 'rgba(124,58,237,0.08)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)'
                e.currentTarget.style.color = '#94A3B8'
                e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
              }}
            >
              View Dashboard
            </Link>
          </div>

          {/* Trust indicators */}
          <div style={{
            display: 'flex', justifyContent: 'center',
            alignItems: 'center', gap: 32, flexWrap: 'wrap',
          }}>
            {['384+ automated tests', '3-tier AI strategy', 'Sub-350ms response', 'Auto-escalation'].map(txt => (
              <span key={txt} style={{
                display: 'flex', alignItems: 'center', gap: 7,
                fontSize: 13.5, color: '#475569',
              }}>
                <CheckCircle size={13} style={{ color: '#10B981', flexShrink: 0 }} />
                {txt}
              </span>
            ))}
          </div>

        </div>
      </section>

      {/* ─── DIVIDER ─────────────────────────────────────────────── */}
      <div style={{ padding: '0 56px' }}>
        <div style={{
          height: 1,
          background: 'linear-gradient(90deg,transparent,rgba(255,255,255,0.08) 20%,rgba(255,255,255,0.08) 80%,transparent)',
        }} />
      </div>

      {/* ─── ACTION CARDS ────────────────────────────────────────── */}
      <section style={{ padding: '100px 56px' }}>
        <div style={{ maxWidth: 1400, margin: '0 auto' }}>

          {/* Section header */}
          <div style={{ textAlign: 'center', marginBottom: 60 }}>
            <h2 style={{
              fontSize: 'clamp(28px,3.5vw,42px)',
              fontWeight: 800, color: '#F1F5F9',
              letterSpacing: '-0.8px', marginBottom: 16,
            }}>
              How can we help?
            </h2>
            <p style={{ fontSize: 17, color: '#94A3B8', maxWidth: 480, margin: '0 auto', lineHeight: 1.7 }}>
              Pick an option below — the AI handles everything from here.
            </p>
          </div>

          {/* Cards grid — 3 equal columns on desktop */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 28,
          }}>
            {CARDS.map(card => <ActionCard key={card.title} {...card} />)}
          </div>
        </div>
      </section>

      {/* ─── STATS ───────────────────────────────────────────────── */}
      <section style={{ padding: '0 56px 100px' }}>
        <div style={{ maxWidth: 1400, margin: '0 auto' }}>

          <div style={{ textAlign: 'center', marginBottom: 52 }}>
            <h2 style={{
              fontSize: 'clamp(26px,3vw,38px)',
              fontWeight: 800, color: '#F1F5F9',
              letterSpacing: '-0.6px', marginBottom: 14,
            }}>
              Built for scale
            </h2>
            <p style={{ fontSize: 16, color: '#94A3B8', lineHeight: 1.7 }}>
              Live metrics from the running AI system
            </p>
          </div>

          {/* 4-column stat row */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4,1fr)',
            background: '#111827',
            borderRadius: 22,
            border: '1px solid rgba(255,255,255,0.07)',
            overflow: 'hidden',
          }}>
            {STATS.map((s, i) => (
              <StatCell key={s.label} stat={s} divider={i < STATS.length - 1} />
            ))}
          </div>
        </div>
      </section>

      {/* ─── FOOTER ──────────────────────────────────────────────── */}
      <footer style={{
        borderTop: '1px solid rgba(255,255,255,0.06)',
        padding: '32px 56px',
        background: '#0B0F19',
      }}>
        <div style={{
          maxWidth: 1400, margin: '0 auto',
          display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', flexWrap: 'wrap', gap: 16,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 30, height: 30, borderRadius: 8,
              background: 'linear-gradient(135deg,#7C3AED,#A855F7)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Zap size={14} color="#fff" />
            </div>
            <span style={{ fontSize: 15, fontWeight: 700, color: '#E2E8F0' }}>Nexora</span>
            <span style={{ fontSize: 13, color: '#334155' }}>— Customer Success Digital FTE</span>
          </div>
          <span style={{ fontSize: 13, color: '#334155' }}>
            Hackathon 5 &middot; Stage 3 &middot; Mehreen Asghar
          </span>
        </div>
      </footer>

    </div>
  )
}

// ─────────────────────────────────────────────────────────────────
// ACTION CARD
// ─────────────────────────────────────────────────────────────────
function ActionCard({ icon: Icon, color, title, description, label, href }: Card) {
  return (
    <div
      style={{
        display: 'flex', flexDirection: 'column',
        padding: '36px 32px 32px',
        borderRadius: 20,
        background: '#111827',
        border: '1px solid rgba(255,255,255,0.07)',
        borderTop: `3px solid ${color}`,
        transition: 'transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease',
        cursor: 'default',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.transform = 'translateY(-5px)'
        e.currentTarget.style.boxShadow = '0 24px 56px rgba(0,0,0,0.5)'
        e.currentTarget.style.borderColor = `${color}40`
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = 'translateY(0)'
        e.currentTarget.style.boxShadow = 'none'
        e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'
      }}
    >
      {/* Icon */}
      <div style={{
        width: 58, height: 58, borderRadius: 15,
        background: `${color}18`,
        border: `1px solid ${color}32`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: 28, flexShrink: 0,
      }}>
        <Icon size={27} style={{ color }} />
      </div>

      {/* Title */}
      <h3 style={{
        fontSize: 21, fontWeight: 700, color: '#F1F5F9',
        letterSpacing: '-0.3px', marginBottom: 13,
      }}>
        {title}
      </h3>

      {/* Description */}
      <p style={{
        fontSize: 14.5, color: '#64748B', lineHeight: 1.78,
        marginBottom: 32, flex: 1,
      }}>
        {description}
      </p>

      {/* Button */}
      <Link
        href={href}
        style={{
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          padding: '12px 24px', borderRadius: 10,
          background: `linear-gradient(135deg,${color},${color}bb)`,
          color: '#fff', fontWeight: 600, fontSize: 14.5,
          textDecoration: 'none',
          transition: 'opacity 0.15s, transform 0.15s',
          alignSelf: 'flex-start',
          boxShadow: `0 3px 14px ${color}30`,
        }}
        onMouseEnter={e => {
          e.currentTarget.style.opacity = '0.86'
          e.currentTarget.style.transform = 'translateY(-1px)'
        }}
        onMouseLeave={e => {
          e.currentTarget.style.opacity = '1'
          e.currentTarget.style.transform = 'translateY(0)'
        }}
      >
        {label} <ArrowRight size={14} />
      </Link>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────
// STAT CELL
// ─────────────────────────────────────────────────────────────────
function StatCell({ stat, divider }: { stat: Stat; divider: boolean }) {
  const { icon: Icon, value, label, color } = stat
  return (
    <div
      style={{
        padding: '48px 36px',
        textAlign: 'center',
        borderRight: divider ? '1px solid rgba(255,255,255,0.06)' : 'none',
        transition: 'background 0.15s',
      }}
      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.025)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
    >
      <div style={{
        width: 52, height: 52, borderRadius: 14,
        background: `${color}18`,
        border: `1px solid ${color}2a`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 22px',
      }}>
        <Icon size={23} style={{ color }} />
      </div>
      <p style={{
        fontSize: 'clamp(32px,3.5vw,48px)',
        fontWeight: 900, color: '#F1F5F9',
        letterSpacing: '-2px', lineHeight: 1, marginBottom: 11,
      }}>
        {value}
      </p>
      <p style={{ fontSize: 14.5, color: '#64748B', fontWeight: 500 }}>{label}</p>
    </div>
  )
}
