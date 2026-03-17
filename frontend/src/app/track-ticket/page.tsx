'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Zap, Moon, Sun, ArrowLeft, Search } from 'lucide-react'
import TicketStatusLookup from '@/components/TicketStatusLookup'

function NavLink({ label, href }: { label: string; href: string }) {
  return (
    <Link
      href={href}
      style={{
        padding: '8px 18px', borderRadius: 8,
        fontSize: 15, fontWeight: 600,
        color: '#94A3B8', textDecoration: 'none',
        transition: 'color .15s, background .15s',
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

export default function TrackTicketPage() {
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
    }}>

      {/* ── Navbar ─────────────────────────────────────────────── */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 100,
        height: 66,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 48px',
        background: atTop ? 'rgba(11,15,25,0.6)' : 'rgba(11,15,25,0.94)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderBottom: atTop ? '1px solid transparent' : '1px solid rgba(255,255,255,0.07)',
        transition: 'background .3s, border-color .3s',
      }}>
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
          <div style={{
            width: 36, height: 36, borderRadius: 9,
            background: 'linear-gradient(135deg,#7C3AED,#A855F7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Zap size={17} color="#fff" />
          </div>
          <span style={{ fontSize: 17, fontWeight: 800, color: '#F1F5F9', letterSpacing: '-0.3px' }}>
            Nexora
          </span>
        </Link>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <NavLink label="Submit Request" href="/support" />
          <NavLink label="Track Ticket"   href="/track-ticket" />
          <NavLink label="Dashboard"      href="/dashboard" />
        </div>

        <button
          onClick={() => setIsDark(v => !v)}
          aria-label="Toggle theme"
          style={{
            width: 38, height: 38, borderRadius: 9,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#64748B', cursor: 'pointer', transition: 'all .15s',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = 'rgba(37,99,235,0.12)'
            e.currentTarget.style.borderColor = 'rgba(37,99,235,0.35)'
            e.currentTarget.style.color = '#93C5FD'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
            e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'
            e.currentTarget.style.color = '#64748B'
          }}
        >
          {isDark ? <Moon size={15} /> : <Sun size={15} />}
        </button>
      </nav>

      {/* ── Hero ───────────────────────────────────────────────── */}
      <section style={{
        position: 'relative',
        textAlign: 'center',
        padding: '72px 48px 56px',
        overflow: 'hidden',
      }}>
        {/* Glow */}
        <div style={{
          position: 'absolute', top: 0, left: '50%', transform: 'translateX(-50%)',
          width: 700, height: 380, borderRadius: '50%',
          background: 'radial-gradient(ellipse at 50% 30%, rgba(37,99,235,0.09) 0%, transparent 65%)',
          pointerEvents: 'none',
        }} />

        {/* Back link */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 28, position: 'relative' }}>
          <Link
            href="/"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              fontSize: 13, color: '#475569', textDecoration: 'none',
              transition: 'color .15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.color = '#93C5FD')}
            onMouseLeave={e => (e.currentTarget.style.color = '#475569')}
          >
            <ArrowLeft size={13} /> Back to home
          </Link>
        </div>

        {/* Icon badge */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          padding: '6px 18px', borderRadius: 99,
          background: 'rgba(37,99,235,0.1)',
          border: '1px solid rgba(37,99,235,0.22)',
          fontSize: 12.5, fontWeight: 600, color: '#93C5FD',
          marginBottom: 28, letterSpacing: '0.4px',
          position: 'relative',
        }}>
          <Search size={12} />
          Ticket Status Lookup
        </div>

        <h1 style={{
          position: 'relative',
          fontSize: 'clamp(28px, 4.5vw, 52px)',
          fontWeight: 900, lineHeight: 1.1,
          letterSpacing: '-1.5px', color: '#F1F5F9',
          maxWidth: 680, margin: '0 auto 16px',
        }}>
          Track Your{' '}
          <span style={{
            background: 'linear-gradient(120deg,#60A5FA 0%,#2563EB 50%,#7C3AED 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}>
            Support Ticket
          </span>
        </h1>

        <p style={{
          position: 'relative',
          fontSize: 'clamp(14px,1.6vw,17px)',
          color: '#94A3B8', lineHeight: 1.75,
          maxWidth: 480, margin: '0 auto',
        }}>
          Enter the ticket reference from your confirmation email to see
          real-time status, priority, and the latest response.
        </p>
      </section>

      {/* ── Divider ─────────────────────────────────────────────── */}
      <div style={{ padding: '0 48px' }}>
        <div style={{
          height: 1,
          background: 'linear-gradient(90deg,transparent,rgba(255,255,255,0.07) 20%,rgba(255,255,255,0.07) 80%,transparent)',
        }} />
      </div>

      {/* ── Lookup card ─────────────────────────────────────────── */}
      <main style={{ maxWidth: 640, margin: '0 auto', padding: '64px 24px 80px' }}>
        <TicketStatusLookup />

        {/* Prompt to submit */}
        <div style={{
          marginTop: 32, padding: '20px 24px', borderRadius: 14,
          background: 'rgba(124,58,237,0.06)',
          border: '1px solid rgba(124,58,237,0.14)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          flexWrap: 'wrap', gap: 14,
        }}>
          <div>
            <p style={{ fontSize: 13.5, fontWeight: 600, color: '#C4B5FD', marginBottom: 3 }}>
              Don&apos;t have a ticket yet?
            </p>
            <p style={{ fontSize: 12.5, color: '#475569' }}>
              Submit a new request and get an instant AI response.
            </p>
          </div>
          <Link
            href="/support"
            style={{
              padding: '9px 20px', borderRadius: 9,
              background: 'linear-gradient(135deg,#7C3AED,#6D28D9)',
              color: '#fff', fontWeight: 600, fontSize: 13.5,
              textDecoration: 'none', flexShrink: 0,
              transition: 'opacity .15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.opacity = '0.85')}
            onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
          >
            Submit a Request
          </Link>
        </div>
      </main>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer style={{
        borderTop: '1px solid rgba(255,255,255,0.06)',
        padding: '28px 48px',
        background: '#0B0F19',
      }}>
        <div style={{
          maxWidth: 1400, margin: '0 auto',
          display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', flexWrap: 'wrap', gap: 16,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
            <div style={{
              width: 28, height: 28, borderRadius: 7,
              background: 'linear-gradient(135deg,#7C3AED,#A855F7)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Zap size={13} color="#fff" />
            </div>
            <span style={{ fontSize: 14, fontWeight: 700, color: '#E2E8F0' }}>Nexora</span>
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
