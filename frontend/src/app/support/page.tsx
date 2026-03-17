'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Zap, Moon, Sun, CheckCircle, ArrowLeft } from 'lucide-react'
import SupportForm from '@/components/SupportForm'
import TicketStatusLookup from '@/components/TicketStatusLookup'

// ─── Page ────────────────────────────────────────────────────────────────────

export default function SupportPage() {
  const [atTop,  setAtTop]  = useState(true)
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

      {/* ── Navbar ─────────────────────────────────────────────────── */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 100,
        height: 68,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 48px',
        background: atTop ? 'rgba(11,15,25,0.6)' : 'rgba(11,15,25,0.94)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderBottom: atTop ? '1px solid transparent' : '1px solid rgba(255,255,255,0.07)',
        transition: 'background .3s, border-color .3s',
      }}>
        {/* Logo */}
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

        {/* Center links */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {[
            { label: 'Submit Request', href: '/support' },
            { label: 'Track Ticket',  href: '/track-ticket' },
            { label: 'Dashboard',     href: '/dashboard' },
          ].map(({ label, href }) => (
            <Link
              key={label}
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
            >{label}</Link>
          ))}
        </div>

        {/* Right: theme toggle */}
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
            e.currentTarget.style.background = 'rgba(124,58,237,0.1)'
            e.currentTarget.style.borderColor = 'rgba(124,58,237,0.3)'
            e.currentTarget.style.color = '#C4B5FD'
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

      {/* ── Hero ───────────────────────────────────────────────────── */}
      <section style={{
        position: 'relative',
        textAlign: 'center',
        padding: '72px 24px 56px',
        overflow: 'hidden',
      }}>
        {/* Subtle glow */}
        <div style={{
          position: 'absolute', top: 0, left: '50%', transform: 'translateX(-50%)',
          width: 700, height: 400, borderRadius: '50%',
          background: 'radial-gradient(ellipse at 50% 30%, rgba(124,58,237,0.08) 0%, transparent 65%)',
          pointerEvents: 'none',
        }} />

        {/* Back link */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 24, position: 'relative' }}>
          <Link
            href="/"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              fontSize: 13, color: '#475569', textDecoration: 'none',
              transition: 'color .15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.color = '#C4B5FD')}
            onMouseLeave={e => (e.currentTarget.style.color = '#475569')}
          >
            <ArrowLeft size={13} /> Back to home
          </Link>
        </div>

        <h1 style={{
          position: 'relative',
          fontSize: 'clamp(30px, 5vw, 52px)',
          fontWeight: 900, lineHeight: 1.1,
          letterSpacing: '-1.5px', color: '#F1F5F9',
          marginBottom: 16,
        }}>
          How can we{' '}
          <span style={{
            background: 'linear-gradient(120deg,#A855F7 0%,#7C3AED 50%,#3B82F6 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}>
            help?
          </span>
        </h1>

        <p style={{
          position: 'relative',
          fontSize: 'clamp(14px,1.6vw,17px)',
          color: '#64748B', lineHeight: 1.75,
          maxWidth: 480, margin: '0 auto 36px',
        }}>
          Our AI support agent responds in seconds.
          For complex issues, a human specialist will follow up.
        </p>

        {/* Trust pills */}
        <div style={{
          position: 'relative',
          display: 'flex', justifyContent: 'center',
          alignItems: 'center', gap: 24, flexWrap: 'wrap',
        }}>
          {[
            'Instant AI response',
            'Ticket reference for tracking',
            'Human escalation when needed',
            'Powered by Claude / GPT-4o',
          ].map(txt => (
            <span key={txt} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              fontSize: 13, color: '#475569',
            }}>
              <CheckCircle size={13} style={{ color: '#059669', flexShrink: 0 }} />
              {txt}
            </span>
          ))}
        </div>
      </section>

      {/* ── Divider ─────────────────────────────────────────────────── */}
      <div style={{ padding: '0 40px' }}>
        <div style={{
          height: 1,
          background: 'linear-gradient(90deg,transparent,rgba(255,255,255,0.07) 20%,rgba(255,255,255,0.07) 80%,transparent)',
        }} />
      </div>

      {/* ── Main content ────────────────────────────────────────────── */}
      <main style={{ maxWidth: 1080, margin: '0 auto', padding: '64px 28px 80px' }}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">

          {/* Left: Submit form */}
          <div>
            <SectionLabel
              title="Submit a Request"
              description="Fill in the form and our AI agent will respond immediately."
            />
            <SupportForm />
          </div>

          {/* Right: Lookup + channels */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div>
              <SectionLabel
                title="Check Ticket Status"
                description="Already submitted? Enter your reference to see the latest update."
              />
              <TicketStatusLookup />
            </div>

            {/* Contact channels */}
            <div style={{
              borderRadius: 16,
              background: '#111827',
              border: '1px solid rgba(255,255,255,0.07)',
              padding: '22px 24px',
            }}>
              <p style={{
                fontSize: 13, fontWeight: 700, color: '#F1F5F9',
                marginBottom: 18, letterSpacing: '0.1px',
              }}>
                Other ways to reach us
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <ContactRow emoji="📧" label="Email"          value="support@nexora.io"   note="Processed by the same AI agent" />
                <ContactRow emoji="💬" label="WhatsApp"       value="+1 415 523 8886"      note="Twilio WhatsApp sandbox" />
                <ContactRow emoji="📖" label="Knowledge Base" value="docs.nexora.io"       note="Self-service articles" />
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* ── Footer ─────────────────────────────────────────────────── */}
      <footer style={{
        borderTop: '1px solid rgba(255,255,255,0.06)',
        padding: '28px 40px',
        background: '#0B0F19',
      }}>
        <div style={{
          maxWidth: 1080, margin: '0 auto',
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

// ─── Sub-components ──────────────────────────────────────────────────────────

function SectionLabel({ title, description }: { title: string; description: string }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <h2 style={{ fontSize: 17, fontWeight: 700, color: '#F1F5F9', marginBottom: 4, letterSpacing: '-0.2px' }}>
        {title}
      </h2>
      <p style={{ fontSize: 13, color: '#64748B' }}>{description}</p>
    </div>
  )
}

function ContactRow({
  emoji, label, value, note,
}: {
  emoji: string; label: string; value: string; note: string
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
      <span style={{
        width: 36, height: 36, borderRadius: 9, flexShrink: 0,
        background: 'rgba(124,58,237,0.08)',
        border: '1px solid rgba(124,58,237,0.15)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 16,
      }}>{emoji}</span>
      <div>
        <p style={{ fontSize: 13, fontWeight: 600, color: '#CBD5E1' }}>
          {label}:{' '}
          <span style={{ color: '#A78BFA', fontWeight: 500 }}>{value}</span>
        </p>
        <p style={{ fontSize: 11.5, color: '#475569', marginTop: 2 }}>{note}</p>
      </div>
    </div>
  )
}
