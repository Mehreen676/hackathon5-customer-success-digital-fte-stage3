'use client'

import { useState } from 'react'
import { CheckCircle, AlertCircle, RefreshCw, Send } from 'lucide-react'
import api from '../lib/api'

// ─── Types ───────────────────────────────────────────────────────────────────

interface FormState {
  name: string
  email: string
  subject: string
  message: string
  channel: string
}

interface SubmissionResult {
  ticket_ref: string
  status: string
  escalated: boolean
  response: string
}

// ─── Constants ───────────────────────────────────────────────────────────────

const SUBJECTS = [
  'Billing question',
  'Account access issue',
  'Integration / API help',
  'Plan upgrade or downgrade',
  'Data export request',
  'Team management',
  'Other',
]

const INITIAL: FormState = { name: '', email: '', subject: '', message: '', channel: 'web_form' }

// ─── Validation ──────────────────────────────────────────────────────────────

function validate(form: FormState): Partial<Record<keyof FormState, string>> {
  const e: Partial<Record<keyof FormState, string>> = {}
  if (!form.name.trim())    e.name    = 'Full name is required.'
  if (!form.email.trim())   e.email   = 'Email address is required.'
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = 'Enter a valid email address.'
  if (!form.subject.trim()) e.subject = 'Please select a subject.'
  if (!form.message.trim()) e.message = 'Message is required.'
  else if (form.message.trim().length < 10) e.message = 'Message must be at least 10 characters.'
  return e
}

// ─── Shared style helpers ────────────────────────────────────────────────────

function inputStyle(hasError: boolean): React.CSSProperties {
  return {
    width: '100%',
    padding: '11px 14px',
    borderRadius: 10,
    background: 'rgba(255,255,255,0.04)',
    border: `1px solid ${hasError ? 'rgba(220,38,38,0.5)' : 'rgba(255,255,255,0.09)'}`,
    color: '#E2E8F0',
    fontSize: 14,
    outline: 'none',
    transition: 'border-color .15s, box-shadow .15s',
    colorScheme: 'dark' as React.CSSProperties['colorScheme'],
  }
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function SupportForm() {
  const [form,   setForm]   = useState<FormState>(INITIAL)
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({})
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState<SubmissionResult | null>(null)
  const [serverErr, setServerErr] = useState<string | null>(null)

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
    if (errors[name as keyof FormState]) setErrors(prev => ({ ...prev, [name]: undefined }))
  }

  function focusStyle(e: React.FocusEvent<HTMLElement>) {
    const el = e.target as HTMLElement
    el.style.borderColor = 'rgba(124,58,237,0.5)'
    el.style.boxShadow   = '0 0 0 3px rgba(124,58,237,0.08)'
  }
  function blurStyle(e: React.FocusEvent<HTMLElement>, hasError: boolean) {
    const el = e.target as HTMLElement
    el.style.borderColor = hasError ? 'rgba(220,38,38,0.5)' : 'rgba(255,255,255,0.09)'
    el.style.boxShadow   = 'none'
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setServerErr(null)
    const errs = validate(form)
    if (Object.keys(errs).length) { setErrors(errs); return }

    setLoading(true)
    try {
      const data = await api.submitSupportForm({
        name: form.name.trim(),
        email: form.email.trim(),
        subject: form.subject.trim(),
        message: form.message.trim(),
      }) as any
      if (data.success && data.ticket?.ticket_ref) {
        setResult({ ticket_ref: data.ticket.ticket_ref, status: data.ticket.status, escalated: data.escalated ?? false, response: data.response ?? '' })
        setForm(INITIAL)
      } else {
        setServerErr('Submission failed. Please try again.')
      }
    } catch (err: any) {
      setServerErr(
        err?.message?.includes('422')
          ? 'Please check all fields and try again.'
          : 'Could not reach the support system. Please try again later.'
      )
    } finally {
      setLoading(false)
    }
  }

  // ── Success state ─────────────────────────────────────────────────
  if (result) {
    return (
      <div style={{
        borderRadius: 18, padding: '28px 28px',
        background: '#111827',
        border: '1px solid rgba(255,255,255,0.07)',
        borderTop: '3px solid #059669',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 24 }}>
          <div style={{
            width: 48, height: 48, borderRadius: 14, flexShrink: 0,
            background: 'rgba(5,150,105,0.12)',
            border: '1px solid rgba(5,150,105,0.25)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <CheckCircle size={22} style={{ color: '#34D399' }} />
          </div>
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 700, color: '#F1F5F9' }}>Request Submitted</h2>
            <p style={{ fontSize: 13, color: '#64748B', marginTop: 2 }}>
              We&apos;ve received your message and are on it.
            </p>
          </div>
        </div>

        {/* Ticket info */}
        <div style={{
          borderRadius: 12, background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.07)',
          padding: '16px 18px', marginBottom: 20,
          display: 'flex', flexDirection: 'column', gap: 12,
        }}>
          <InfoRow label="Ticket reference">
            <span style={{ fontFamily: 'monospace', fontWeight: 800, fontSize: 16, color: '#C4B5FD' }}>
              {result.ticket_ref}
            </span>
          </InfoRow>
          <InfoRow label="Status">
            <StatusPill status={result.status} />
          </InfoRow>
          {result.escalated && (
            <InfoRow label="Priority">
              <span style={{ fontSize: 13, fontWeight: 600, color: '#FCA5A5' }}>
                Escalated to human agent
              </span>
            </InfoRow>
          )}
        </div>

        {/* AI response */}
        {result.response && (
          <div style={{ marginBottom: 20 }}>
            <p style={{ fontSize: 11, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 10 }}>
              Initial response from our agent
            </p>
            <div style={{
              borderRadius: 12, padding: '14px 16px',
              background: 'rgba(124,58,237,0.07)',
              border: '1px solid rgba(124,58,237,0.18)',
              fontSize: 13.5, color: '#CBD5E1', lineHeight: 1.7,
              whiteSpace: 'pre-wrap',
            }}>
              {result.response}
            </div>
          </div>
        )}

        <p style={{ fontSize: 12, color: '#334155', marginBottom: 18 }}>
          Save your ticket reference — you can use it to check your request status any time.
        </p>

        <button
          onClick={() => setResult(null)}
          style={{
            width: '100%', padding: '11px 20px', borderRadius: 10,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.1)',
            color: '#94A3B8', fontSize: 14, fontWeight: 600,
            cursor: 'pointer', transition: 'all .15s',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = 'rgba(124,58,237,0.08)'
            e.currentTarget.style.borderColor = 'rgba(124,58,237,0.25)'
            e.currentTarget.style.color = '#C4B5FD'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
            e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'
            e.currentTarget.style.color = '#94A3B8'
          }}
        >
          Submit another request
        </button>
      </div>
    )
  }

  // ── Form state ────────────────────────────────────────────────────
  return (
    <div style={{
      borderRadius: 18, padding: '28px',
      background: '#111827',
      border: '1px solid rgba(255,255,255,0.07)',
      borderTop: '3px solid #7C3AED',
    }}>
      <div style={{ marginBottom: 22 }}>
        <h2 style={{ fontSize: 17, fontWeight: 700, color: '#F1F5F9', marginBottom: 4 }}>Contact Support</h2>
        <p style={{ fontSize: 13, color: '#64748B' }}>
          Describe your issue and our AI agent will respond immediately.
        </p>
      </div>

      {/* Server error */}
      {serverErr && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '12px 14px', borderRadius: 10, marginBottom: 18,
          background: 'rgba(220,38,38,0.08)',
          border: '1px solid rgba(220,38,38,0.25)',
        }}>
          <AlertCircle size={15} style={{ color: '#F87171', flexShrink: 0 }} />
          <span style={{ fontSize: 13, color: '#FCA5A5' }}>{serverErr}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* Name */}
        <DarkField label="Full name" error={errors.name} required>
          <input
            type="text" name="name" value={form.name} onChange={handleChange}
            placeholder="Jane Smith" autoComplete="name"
            style={inputStyle(!!errors.name)}
            onFocus={focusStyle}
            onBlur={e => blurStyle(e, !!errors.name)}
          />
        </DarkField>

        {/* Email */}
        <DarkField label="Email address" error={errors.email} required>
          <input
            type="email" name="email" value={form.email} onChange={handleChange}
            placeholder="jane@company.com" autoComplete="email"
            style={inputStyle(!!errors.email)}
            onFocus={focusStyle}
            onBlur={e => blurStyle(e, !!errors.email)}
          />
        </DarkField>

        {/* Subject */}
        <DarkField label="Subject" error={errors.subject} required>
          <select
            name="subject" value={form.subject} onChange={handleChange}
            style={{ ...inputStyle(!!errors.subject), cursor: 'pointer' }}
            onFocus={focusStyle}
            onBlur={e => blurStyle(e, !!errors.subject)}
          >
            <option value="" style={{ background: '#111827' }}>Select a topic…</option>
            {SUBJECTS.map(s => (
              <option key={s} value={s} style={{ background: '#111827', color: '#E2E8F0' }}>{s}</option>
            ))}
          </select>
        </DarkField>

        {/* Message */}
        <DarkField label="Message" error={errors.message} required>
          <textarea
            name="message" value={form.message} onChange={handleChange}
            placeholder="Describe your issue in as much detail as possible…"
            rows={5}
            style={{ ...inputStyle(!!errors.message), resize: 'none' }}
            onFocus={focusStyle}
            onBlur={e => blurStyle(e, !!errors.message)}
          />
          <p style={{ fontSize: 11.5, color: '#334155', marginTop: 5 }}>
            {form.message.length}/2000 characters
          </p>
        </DarkField>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%', padding: '13px 20px', borderRadius: 10,
            background: loading ? 'rgba(124,58,237,0.5)' : 'linear-gradient(135deg,#7C3AED,#6D28D9)',
            border: '1px solid rgba(124,58,237,0.4)',
            color: '#fff', fontSize: 15, fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'transform .18s, box-shadow .18s',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          }}
          onMouseEnter={e => {
            if (!loading) {
              e.currentTarget.style.transform = 'translateY(-1px)'
              e.currentTarget.style.boxShadow = '0 6px 20px rgba(124,58,237,0.3)'
            }
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = 'none'
          }}
        >
          {loading ? (
            <><RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} /> Processing…</>
          ) : (
            <><Send size={15} /> Submit Request</>
          )}
        </button>
      </form>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function DarkField({
  label, error, required, children,
}: {
  label: string; error?: string; required?: boolean; children: React.ReactNode
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <label style={{ fontSize: 13, fontWeight: 600, color: '#94A3B8' }}>
        {label}
        {required && <span style={{ color: '#F87171', marginLeft: 3 }}>*</span>}
      </label>
      {children}
      {error && (
        <p style={{ fontSize: 12, color: '#F87171', display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
          <AlertCircle size={11} /> {error}
        </p>
      )}
    </div>
  )
}

function InfoRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span style={{ fontSize: 13, color: '#64748B' }}>{label}</span>
      {children}
    </div>
  )
}

function StatusPill({ status }: { status: string }) {
  const map: Record<string, { bg: string; color: string; border: string }> = {
    'open':          { bg: 'rgba(37,99,235,0.12)',  color: '#93C5FD', border: 'rgba(37,99,235,0.25)' },
    'auto-resolved': { bg: 'rgba(5,150,105,0.12)',  color: '#6EE7B7', border: 'rgba(5,150,105,0.25)' },
    'escalated':     { bg: 'rgba(220,38,38,0.12)',  color: '#FCA5A5', border: 'rgba(220,38,38,0.25)' },
    'pending_review':{ bg: 'rgba(217,119,6,0.12)',  color: '#FCD34D', border: 'rgba(217,119,6,0.25)' },
    'closed':        { bg: 'rgba(100,116,139,0.1)', color: '#94A3B8', border: 'rgba(100,116,139,0.2)' },
  }
  const s = map[status] ?? map.closed
  return (
    <span style={{
      fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 99,
      background: s.bg, color: s.color, border: `1px solid ${s.border}`,
      textTransform: 'capitalize',
    }}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}
