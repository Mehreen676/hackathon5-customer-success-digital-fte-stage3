'use client'

import { useState } from 'react'
import api from '@/lib/api'

type TabKey = 'email' | 'whatsapp' | 'webform' | 'generic'

const INITIAL_PAYLOADS: Record<TabKey, Record<string, string>> = {
  email: {
    from_email: 'test@example.com',
    from_name: 'Test User',
    subject: 'Need help with billing',
    body: 'Hi, I cannot access my invoice from last month. Could you help me locate it?',
    customer_id: '',
  },
  whatsapp: {
    from_phone: '+1234567890',
    message_text: 'Hi I need help resetting my password',
    customer_id: '',
  },
  webform: {
    name: 'Test User',
    email: 'test@example.com',
    subject: 'Integration question',
    message: 'How do I connect Nexora to Slack? I cannot find the integration settings.',
    customer_id: '',
  },
  generic: {
    customer_id: 'CUST-001',
    channel: 'web_form',
    content: 'How do I export my project data?',
  },
}

function colorizeJson(json: string): string {
  return json
    .replace(/("[\w]+")\s*:/g, '<span class="json-key">$1</span>:')
    .replace(/:\s*(".*?")/g, ': <span class="json-string">$1</span>')
    .replace(/:\s*(\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
    .replace(/:\s*(true|false)/g, ': <span class="json-bool">$1</span>')
    .replace(/:\s*(null)/g, ': <span class="json-null">$1</span>')
}

export default function ApiTesterPanel() {
  const [activeTab, setActiveTab] = useState<TabKey>('email')
  const [payloads, setPayloads] = useState(INITIAL_PAYLOADS)
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  const tabs: { key: TabKey; label: string; icon: string; endpoint: string }[] = [
    { key: 'email',    label: 'Email',    icon: '📧', endpoint: 'POST /support/gmail' },
    { key: 'whatsapp', label: 'WhatsApp', icon: '📱', endpoint: 'POST /support/whatsapp' },
    { key: 'webform',  label: 'Web Form', icon: '🌐', endpoint: 'POST /support/webform' },
    { key: 'generic',  label: 'Generic',  icon: '🔌', endpoint: 'POST /support/message' },
  ]

  const updateField = (key: string, value: string) => {
    setPayloads((prev) => ({
      ...prev,
      [activeTab]: { ...prev[activeTab], [key]: value },
    }))
  }

  const handleSend = async () => {
    setLoading(true)
    setResponse(null)
    setError(null)

    try {
      const payload = payloads[activeTab]
      let result

      if (activeTab === 'email') {
        result = await api.sendEmail(payload as Parameters<typeof api.sendEmail>[0])
      } else if (activeTab === 'whatsapp') {
        result = await api.sendWhatsApp(payload as Parameters<typeof api.sendWhatsApp>[0])
      } else if (activeTab === 'webform') {
        result = await api.sendWebForm(payload as Parameters<typeof api.sendWebForm>[0])
      } else {
        result = await api.sendMessage(payload as unknown as Parameters<typeof api.sendMessage>[0])
      }

      setResponse(result as Record<string, unknown>)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  const currentPayload = payloads[activeTab]
  const currentTab = tabs.find((t) => t.key === activeTab)!

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Request panel */}
      <div className="card">
        <h3 className="font-semibold text-gray-800 mb-4">Request Builder</h3>

        {/* Tabs */}
        <div className="flex gap-1 mb-4 border-b border-gray-200">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => { setActiveTab(tab.key); setResponse(null); setError(null) }}
              className={`px-3 py-2 text-sm font-medium transition-colors rounded-t-lg -mb-px border-b-2 ${
                activeTab === tab.key
                  ? 'border-purple-600 text-purple-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Endpoint badge */}
        <div className="flex items-center gap-2 mb-4">
          <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-mono rounded">POST</span>
          <span className="text-xs font-mono text-gray-600">{currentTab.endpoint}</span>
        </div>

        {/* Fields */}
        <div className="space-y-3">
          {Object.entries(currentPayload).map(([key, value]) => (
            <div key={key}>
              <label className="block text-xs font-semibold text-gray-500 mb-1 uppercase tracking-wider">
                {key.replace(/_/g, ' ')}
              </label>
              {(key === 'body' || key === 'message' || key === 'content') ? (
                <textarea
                  value={value}
                  onChange={(e) => updateField(key, e.target.value)}
                  rows={3}
                  className="input-field resize-none font-mono text-xs"
                />
              ) : (
                <input
                  type="text"
                  value={value}
                  onChange={(e) => updateField(key, e.target.value)}
                  placeholder={key === 'customer_id' ? 'Leave blank for auto-assign' : ''}
                  className="input-field font-mono text-xs"
                />
              )}
            </div>
          ))}
        </div>

        <button
          onClick={handleSend}
          disabled={loading}
          className="btn-primary mt-5 w-full"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Sending…
            </span>
          ) : (
            'Send Request ➜'
          )}
        </button>
      </div>

      {/* Response panel */}
      <div className="card">
        <h3 className="font-semibold text-gray-800 mb-4">Response</h3>

        {!response && !error && (
          <div className="text-gray-400 text-sm flex flex-col items-center justify-center h-64 gap-2">
            <span className="text-3xl">🔌</span>
            <span>Send a request to see the response here</span>
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-700 text-sm font-semibold mb-1">Request Failed</p>
            <p className="text-red-600 text-xs font-mono">{error}</p>
            <p className="text-red-500 text-xs mt-2">Is the backend running? Run: <code className="bg-red-100 px-1 rounded">uvicorn src.api.main:app --reload</code></p>
          </div>
        )}

        {response && (
          <div className="space-y-3">
            {/* Summary highlights */}
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Channel',    value: String(response.channel || '—') },
                { label: 'Intent',     value: String(response.intent || '—') },
                { label: 'Escalated',  value: Boolean(response.escalated) ? '⚠️ Yes' : '✅ No' },
                { label: 'KB Used',    value: Boolean(response.kb_used)    ? '✅ Yes' : '❌ No' },
                { label: 'AI Used',    value: (response as {ai_used?: boolean}).ai_used     ? '🤖 Yes' : '—' },
                { label: 'Ticket',     value: (response.ticket as {ticket_ref?: string})?.ticket_ref ?? '—' },
              ].map(({ label, value }) => (
                <div key={label} className="px-3 py-2 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-400">{label}</p>
                  <p className="text-sm font-medium text-gray-800">{value}</p>
                </div>
              ))}
            </div>

            {/* Response text */}
            {Boolean(response.response) && (
              <div className="p-3 bg-purple-50 border border-purple-100 rounded-lg">
                <p className="text-xs font-semibold text-purple-600 mb-1">Agent Response</p>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{String(response.response)}</p>
              </div>
            )}

            {/* Raw JSON */}
            <details className="group">
              <summary className="cursor-pointer text-xs font-semibold text-gray-500 hover:text-gray-700">
                Raw JSON response ▾
              </summary>
              <pre
                className="mt-2 p-3 bg-gray-900 text-gray-100 rounded-lg text-xs overflow-auto max-h-64 font-mono"
                dangerouslySetInnerHTML={{
                  __html: colorizeJson(JSON.stringify(response, null, 2)),
                }}
              />
            </details>
          </div>
        )}
      </div>
    </div>
  )
}
