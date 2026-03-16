'use client'

import { useState } from 'react'
import api from '@/lib/api'

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

const CHANNELS = [
  { value: 'web_form', label: 'Web Form (standard)' },
  { value: 'email', label: 'Email (async)' },
]

const SUBJECTS = [
  'Billing question',
  'Account access issue',
  'Integration / API help',
  'Plan upgrade or downgrade',
  'Data export request',
  'Team management',
  'Other',
]

function validate(form: FormState): Partial<Record<keyof FormState, string>> {
  const errors: Partial<Record<keyof FormState, string>> = {}
  if (!form.name.trim()) errors.name = 'Full name is required.'
  if (!form.email.trim()) errors.email = 'Email address is required.'
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
    errors.email = 'Enter a valid email address.'
  if (!form.subject.trim()) errors.subject = 'Please select or enter a subject.'
  if (!form.message.trim()) errors.message = 'Message is required.'
  else if (form.message.trim().length < 10)
    errors.message = 'Message must be at least 10 characters.'
  return errors
}

export default function SupportForm() {
  const [form, setForm] = useState<FormState>({
    name: '',
    email: '',
    subject: '',
    message: '',
    channel: 'web_form',
  })
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({})
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SubmissionResult | null>(null)
  const [serverError, setServerError] = useState<string | null>(null)

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    // Clear field error on change
    if (errors[name as keyof FormState]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }))
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setServerError(null)

    const validationErrors = validate(form)
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors)
      return
    }

    setLoading(true)
    try {
      const data = await api.submitSupportForm({
        name: form.name.trim(),
        email: form.email.trim(),
        subject: form.subject.trim(),
        message: form.message.trim(),
      }) as any

      if (data.success && data.ticket?.ticket_ref) {
        setResult({
          ticket_ref: data.ticket.ticket_ref,
          status: data.ticket.status,
          escalated: data.escalated ?? false,
          response: data.response ?? '',
        })
        setForm({ name: '', email: '', subject: '', message: '', channel: 'web_form' })
      } else {
        setServerError('Submission failed. Please try again.')
      }
    } catch (err: any) {
      setServerError(
        err?.message?.includes('422')
          ? 'Please check all fields and try again.'
          : 'Could not reach the support system. Please try again later.'
      )
    } finally {
      setLoading(false)
    }
  }

  // ── Success state ──────────────────────────────────────────────────
  if (result) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 max-w-xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center text-2xl">
            ✅
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Request Submitted</h2>
            <p className="text-sm text-gray-500">
              We&apos;ve received your message and are on it.
            </p>
          </div>
        </div>

        <div className="bg-gray-50 rounded-xl p-5 mb-6 space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500">Ticket reference</span>
            <span className="font-mono font-bold text-purple-700 text-lg">
              {result.ticket_ref}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500">Status</span>
            <StatusBadge status={result.status} />
          </div>
          {result.escalated && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500">Priority</span>
              <span className="text-sm font-medium text-red-600">
                Escalated to human agent
              </span>
            </div>
          )}
        </div>

        {result.response && (
          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-2">
              Initial response from our agent:
            </h3>
            <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
              {result.response}
            </div>
          </div>
        )}

        <p className="text-xs text-gray-400 mb-4">
          Save your ticket reference — you can use it to check your request status any time.
        </p>

        <button
          onClick={() => setResult(null)}
          className="w-full py-2.5 px-4 rounded-xl border border-gray-300 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Submit another request
        </button>
      </div>
    )
  }

  // ── Form state ─────────────────────────────────────────────────────
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 max-w-xl mx-auto">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900">Contact Support</h2>
        <p className="text-sm text-gray-500 mt-1">
          Describe your issue and our AI agent will respond immediately.
        </p>
      </div>

      {serverError && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          {serverError}
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {/* Name */}
        <Field label="Full name" error={errors.name} required>
          <input
            type="text"
            name="name"
            value={form.name}
            onChange={handleChange}
            placeholder="Jane Smith"
            className={inputClass(!!errors.name)}
          />
        </Field>

        {/* Email */}
        <Field label="Email address" error={errors.email} required>
          <input
            type="email"
            name="email"
            value={form.email}
            onChange={handleChange}
            placeholder="jane@company.com"
            className={inputClass(!!errors.email)}
          />
        </Field>

        {/* Subject */}
        <Field label="Subject" error={errors.subject} required>
          <select
            name="subject"
            value={form.subject}
            onChange={handleChange}
            className={inputClass(!!errors.subject)}
          >
            <option value="">Select a topic…</option>
            {SUBJECTS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </Field>

        {/* Message */}
        <Field label="Message" error={errors.message} required>
          <textarea
            name="message"
            value={form.message}
            onChange={handleChange}
            placeholder="Describe your issue in as much detail as possible…"
            rows={5}
            className={inputClass(!!errors.message) + ' resize-none'}
          />
          <p className="text-xs text-gray-400 mt-1">
            {form.message.length}/2000 characters
          </p>
        </Field>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 px-6 rounded-xl bg-purple-600 text-white font-medium text-sm
                     hover:bg-purple-700 disabled:opacity-60 disabled:cursor-not-allowed
                     transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Processing…
            </span>
          ) : (
            'Submit Request'
          )}
        </button>
      </form>
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────

function Field({
  label,
  error,
  required,
  children,
}: {
  label: string
  error?: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </div>
  )
}

function inputClass(hasError: boolean) {
  return [
    'w-full px-3.5 py-2.5 rounded-xl border text-sm',
    'focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent',
    'transition-colors',
    hasError
      ? 'border-red-400 bg-red-50'
      : 'border-gray-300 bg-white hover:border-gray-400',
  ].join(' ')
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    open: 'bg-blue-100 text-blue-700',
    'auto-resolved': 'bg-green-100 text-green-700',
    escalated: 'bg-red-100 text-red-700',
    pending_review: 'bg-yellow-100 text-yellow-700',
    closed: 'bg-gray-100 text-gray-600',
  }
  return (
    <span
      className={`text-xs font-medium px-2.5 py-1 rounded-full ${map[status] ?? 'bg-gray-100 text-gray-600'}`}
    >
      {status.replace(/_/g, ' ')}
    </span>
  )
}
