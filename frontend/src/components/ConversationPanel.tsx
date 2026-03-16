'use client'

import { useState } from 'react'
import { Send, Paperclip, Smile } from 'lucide-react'
import api from '@/lib/api'

interface Message {
  role: 'customer' | 'agent'
  content: string
  timestamp: string
}

interface Conversation {
  id: string
  customer: string
  initials: string
  avatarColor: string
  channel: 'email' | 'whatsapp' | 'web_form'
  status: 'active' | 'escalated' | 'resolved'
  lastMessage: string
  timestamp: string
  messages: Message[]
}

const MOCK_CONVERSATIONS: Conversation[] = [
  {
    id: 'conv-001',
    customer: 'Sarah Chen',
    initials: 'SC',
    avatarColor: 'linear-gradient(135deg,#7c3aed,#3b82f6)',
    channel: 'email',
    status: 'active',
    lastMessage: 'I need help with my billing invoice',
    timestamp: '2m ago',
    messages: [
      { role: 'customer', content: 'Hi, I cannot find my invoice from last month. Could you help?', timestamp: '10:21 AM' },
      { role: 'agent', content: 'Dear Sarah,\n\nThank you for reaching out. You can access all your invoices from the Billing section in your dashboard under Settings → Billing → Invoice History.\n\nBest regards,\nNexora Customer Success Team', timestamp: '10:21 AM' },
      { role: 'customer', content: 'Perfect, found it! Thank you!', timestamp: '10:23 AM' },
    ],
  },
  {
    id: 'conv-002',
    customer: 'James Liu',
    initials: 'JL',
    avatarColor: 'linear-gradient(135deg,#059669,#0891b2)',
    channel: 'whatsapp',
    status: 'escalated',
    lastMessage: 'Urgent: need refund immediately',
    timestamp: '5m ago',
    messages: [
      { role: 'customer', content: 'I was charged twice for the same month. I need an immediate refund!', timestamp: '10:15 AM' },
      { role: 'agent', content: "Hi James! 👋 I'm really sorry about this billing issue. I've flagged it as a priority and our billing team will be in touch within 1 business day. Ticket #TKT-0042 created. 😊", timestamp: '10:15 AM' },
    ],
  },
  {
    id: 'conv-003',
    customer: 'Priya Sharma',
    initials: 'PS',
    avatarColor: 'linear-gradient(135deg,#db2777,#7c3aed)',
    channel: 'web_form',
    status: 'resolved',
    lastMessage: 'How do I set up SSO?',
    timestamp: '1h ago',
    messages: [
      { role: 'customer', content: 'We need to set up Single Sign-On for our enterprise account. Where do I start?', timestamp: '09:10 AM' },
      { role: 'agent', content: 'Hi Priya,\n\nThanks for contacting us! SSO setup is available on Business and Enterprise plans. Go to Settings → Security → SSO Configuration and follow the SAML 2.0 setup guide.\n\nTicket #TKT-0041 created for reference.\n\nNexora Support Team', timestamp: '09:10 AM' },
      { role: 'customer', content: 'Got it, all configured now. Thanks!', timestamp: '09:45 AM' },
    ],
  },
]

const CHANNEL_BADGE: Record<string, { label: string; cls: string }> = {
  email:    { label: 'Email',     cls: 'badge-blue'  },
  whatsapp: { label: 'WhatsApp',  cls: 'badge-green' },
  web_form: { label: 'Web Form',  cls: 'badge-cyan'  },
}

const STATUS_BADGE: Record<string, string> = {
  active:   'badge-green',
  escalated:'badge-red',
  resolved: 'badge-gray',
}

export default function ConversationPanel() {
  const [conversations] = useState<Conversation[]>(MOCK_CONVERSATIONS)
  const [selected, setSelected] = useState<Conversation>(MOCK_CONVERSATIONS[0])
  const [newMessage, setNewMessage] = useState('')
  const [channel, setChannel] = useState<'email' | 'whatsapp' | 'web_form'>('web_form')
  const [sending, setSending] = useState(false)
  const [sendResult, setSendResult] = useState<string | null>(null)

  const handleSend = async () => {
    if (!newMessage.trim()) return
    setSending(true)
    setSendResult(null)
    try {
      const result = await api.sendMessage({ customer_id: 'DEMO-001', channel, content: newMessage }) as Record<string, unknown>
      setSendResult(`Sent! Response: ${(result as { response?: string }).response?.slice(0, 100) ?? 'OK'}…`)
    } catch (err) {
      setSendResult(err instanceof Error ? err.message : 'Send failed — is backend running?')
    } finally {
      setSending(false)
      setNewMessage('')
    }
  }

  return (
    <div className="flex h-full gap-4">
      {/* Conversation list */}
      <div className="flex-shrink-0" style={{ width: 280 }}>
        <div className="card-dark p-0 overflow-hidden flex flex-col h-full">
          <div className="px-4 py-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Recent Conversations</h3>
          </div>
          <div className="flex-1 overflow-y-auto divide-y" style={{ divideColor: 'rgba(255,255,255,0.04)' }}>
            {conversations.map((conv) => {
              const isSelected = selected.id === conv.id
              const ch = CHANNEL_BADGE[conv.channel]
              return (
                <button
                  key={conv.id}
                  onClick={() => setSelected(conv)}
                  className="w-full text-left px-4 py-3 transition-all"
                  style={{
                    background: isSelected ? 'rgba(139,92,246,0.1)' : 'transparent',
                    borderLeft: isSelected ? '2px solid #a78bfa' : '2px solid transparent',
                  }}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                      style={{ background: conv.avatarColor }}
                    >
                      {conv.initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-sm font-medium text-white truncate">{conv.customer}</span>
                        <span className="text-xs text-gray-600 flex-shrink-0 ml-1">{conv.timestamp}</span>
                      </div>
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className={`badge-dark ${ch.cls} text-[10px] px-1.5 py-0`}>{ch.label}</span>
                        <span className={`badge-dark ${STATUS_BADGE[conv.status]} text-[10px] px-1.5 py-0`}>{conv.status}</span>
                      </div>
                      <p className="text-xs text-gray-600 truncate">{conv.lastMessage}</p>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Conversation detail */}
      <div className="flex-1 flex flex-col gap-4 min-w-0">
        {/* Messages */}
        <div className="card-dark flex-1 flex flex-col p-0 overflow-hidden">
          <div className="px-4 py-3 flex items-center justify-between flex-shrink-0" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            <div className="flex items-center gap-3">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white"
                style={{ background: selected.avatarColor }}
              >
                {selected.initials}
              </div>
              <div>
                <span className="text-sm font-semibold text-white">{selected.customer}</span>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className={`badge-dark ${CHANNEL_BADGE[selected.channel].cls} text-[10px] px-1.5 py-0`}>
                    {CHANNEL_BADGE[selected.channel].label}
                  </span>
                </div>
              </div>
            </div>
            <span className={`badge-dark ${STATUS_BADGE[selected.status]}`}>{selected.status}</span>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {selected.messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'agent' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className="max-w-[75%] px-4 py-3 rounded-2xl text-sm whitespace-pre-wrap"
                  style={
                    msg.role === 'agent'
                      ? {
                          background: 'linear-gradient(135deg,rgba(124,58,237,0.8),rgba(59,130,246,0.6))',
                          color: '#f1f5f9',
                          borderBottomRightRadius: 4,
                          boxShadow: '0 0 16px rgba(139,92,246,0.2)',
                        }
                      : {
                          background: 'rgba(255,255,255,0.06)',
                          border: '1px solid rgba(255,255,255,0.08)',
                          color: '#d1d5db',
                          borderBottomLeftRadius: 4,
                        }
                  }
                >
                  {msg.content}
                  <div className="text-[10px] mt-1.5 opacity-60">{msg.timestamp}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Send new message */}
        <div className="card-dark">
          <div className="flex items-center gap-3 mb-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Send to AI Agent</p>
            <select
              value={channel}
              onChange={(e) => setChannel(e.target.value as typeof channel)}
              className="input-dark w-36 py-1 text-xs ml-auto"
            >
              <option value="email">Email</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="web_form">Web Form</option>
            </select>
          </div>
          <textarea
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder="Type a message to test the AI agent…"
            rows={3}
            className="input-dark resize-none mb-3"
          />
          <div className="flex items-center gap-2">
            <button
              onClick={handleSend}
              disabled={sending || !newMessage.trim()}
              className="btn-primary flex items-center gap-2"
            >
              <Send size={13} />
              {sending ? 'Sending…' : 'Send Reply'}
            </button>
            <button className="btn-ghost p-2" title="Attach file"><Paperclip size={14} /></button>
            <button className="btn-ghost p-2" title="Emoji"><Smile size={14} /></button>
            {sendResult && (
              <p className="text-xs text-gray-500 flex-1 ml-1 truncate">{sendResult}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
