/**
 * Support Page — Nexora Customer Support
 *
 * Public-facing support page at /support.
 * Renders the support form and ticket status lookup side by side on desktop,
 * stacked on mobile.  No authentication required.
 */

import type { Metadata } from 'next'
import SupportForm from '@/components/SupportForm'
import TicketStatusLookup from '@/components/TicketStatusLookup'

export const metadata: Metadata = {
  title: 'Get Support | Nexora',
  description:
    'Contact the Nexora support team. Submit a request and receive an AI-powered response in seconds, or look up an existing ticket.',
}

export default function SupportPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-purple-50 via-white to-gray-50">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center">
              <svg
                className="w-5 h-5 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <span className="font-semibold text-gray-900">Nexora Support</span>
          </div>
          <a
            href="/"
            className="text-sm text-purple-600 hover:text-purple-700 font-medium transition-colors"
          >
            ← Dashboard
          </a>
        </div>
      </header>

      {/* ── Hero ───────────────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 pt-12 pb-8 text-center">
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-3">
          How can we help?
        </h1>
        <p className="text-gray-500 text-lg max-w-2xl mx-auto">
          Our AI support agent responds in seconds.
          <br className="hidden sm:block" />
          For complex issues, a human specialist will follow up.
        </p>

        {/* Quick facts */}
        <div className="flex flex-wrap justify-center gap-6 mt-8 text-sm text-gray-500">
          <Stat icon="⚡" label="Instant AI response" />
          <Stat icon="🎫" label="Ticket reference for tracking" />
          <Stat icon="👤" label="Human escalation when needed" />
          <Stat icon="📊" label="Powered by Claude / GPT-4o" />
        </div>
      </section>

      {/* ── Main content ───────────────────────────────────────────── */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 pb-20">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
          {/* Support form */}
          <div>
            <SectionHeading
              title="Submit a Request"
              description="Fill in the form and our AI agent will respond immediately."
            />
            <SupportForm />
          </div>

          {/* Ticket lookup */}
          <div>
            <SectionHeading
              title="Check Ticket Status"
              description="Already submitted? Enter your reference to see the latest update."
            />
            <TicketStatusLookup />

            {/* Channel info */}
            <div className="mt-6 bg-white rounded-2xl border border-gray-200 p-6">
              <h3 className="text-sm font-semibold text-gray-800 mb-4">Other ways to reach us</h3>
              <div className="space-y-3">
                <ChannelRow
                  icon="📧"
                  label="Email"
                  value="support@nexora.io"
                  note="Processed by the same AI agent"
                />
                <ChannelRow
                  icon="💬"
                  label="WhatsApp"
                  value="+1 415 523 8886"
                  note="Twilio WhatsApp sandbox"
                />
                <ChannelRow
                  icon="📖"
                  label="Knowledge Base"
                  value="docs.nexora.io"
                  note="Self-service articles"
                />
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* ── Footer ─────────────────────────────────────────────────── */}
      <footer className="border-t border-gray-200 bg-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row justify-between items-center gap-2 text-xs text-gray-400">
          <span>Nexora Customer Success Digital FTE — Stage 3</span>
          <span>Hackathon 5 · Mehreen Asghar</span>
        </div>
      </footer>
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────

function Stat({ icon, label }: { icon: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span>{icon}</span>
      <span>{label}</span>
    </div>
  )
}

function SectionHeading({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold text-gray-800">{title}</h2>
      <p className="text-sm text-gray-500">{description}</p>
    </div>
  )
}

function ChannelRow({
  icon,
  label,
  value,
  note,
}: {
  icon: string
  label: string
  value: string
  note: string
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="text-lg">{icon}</span>
      <div>
        <p className="text-sm font-medium text-gray-700">
          {label}: <span className="text-purple-700">{value}</span>
        </p>
        <p className="text-xs text-gray-400">{note}</p>
      </div>
    </div>
  )
}
