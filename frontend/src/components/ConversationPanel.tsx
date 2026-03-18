'use client'

import { useState, useEffect } from 'react'
import { Send, Paperclip, Smile, MessageSquare } from 'lucide-react'
import api, { TicketListItem } from '../lib/api'

interface Message {
  role: 'customer' | 'agent'
  content: string
  timestamp: string
}

interface Conversation {
  id: string
  customer: string
  avatar: string
  channel: 'email' | 'whatsapp' | 'web_form'
  status: 'active' | 'escalated' | 'resolved'
  lastMessage: string
  timestamp: string
  messages: Message[]
}

function ticketToConversation(t: TicketListItem): Conversation {
  let status: Conversation['status'] = 'active'
  if (t.escalated || t.status === 'escalated') status = 'escalated'
  else if (t.status === 'auto-resolved' || t.status === 'closed') status = 'resolved'

  const messages: Message[] = []
  if (t.description) {
    messages.push({ role: 'customer', content: t.description, timestamp: t.created_at })
  }

  return {
    id: t.ticket_ref,
    customer: t.customer,
    avatar: `https://i.pravatar.cc/150?u=${encodeURIComponent(t.customer)}`,
    channel: (t.channel as Conversation['channel']) || 'web_form',
    status,
    lastMessage: t.subject,
    timestamp: t.created_at,
    messages,
  }
}

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
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selected, setSelected] = useState<Conversation | null>(null)
  const [newMessage, setNewMessage] = useState('')
  const [channel, setChannel] = useState<'email' | 'whatsapp' | 'web_form'>('web_form')
  const [sending, setSending] = useState(false)
  const [sendResult, setSendResult] = useState<string | null>(null)

  useEffect(() => {
    api.getTickets(50).then((tickets) => {
      const convs = tickets.map(ticketToConversation)
      setConversations(convs)
    })
  }, [])

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
    <div className="flex h-full gap-5">
      {/* Conversation list */}
      <div className="flex-shrink-0" style={{ width: 320 }}>
        <div className="card p-0 overflow-hidden flex flex-col h-full">
          <div className="px-6 py-5" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            <h3 className="text-base font-bold text-white">Recent Conversations</h3>
            <p className="text-sm text-gray-600 mt-0.5">Live customer interactions</p>
          </div>
          <div className="flex-1 overflow-y-auto">
            {conversations.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
                <MessageSquare size={32} style={{ color: 'rgba(255,255,255,0.1)', marginBottom: 12 }} />
                <p className="text-sm font-semibold" style={{ color: 'rgba(255,255,255,0.25)' }}>No conversations yet</p>
                <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.12)' }}>Submitted tickets will appear here</p>
              </div>
            ) : (
              conversations.map((conv) => {
                const isSelected = selected?.id === conv.id
                const ch = CHANNEL_BADGE[conv.channel] ?? CHANNEL_BADGE.web_form
                return (
                  <button
                    key={conv.id}
                    onClick={() => setSelected(conv)}
                    className="w-full text-left px-6 py-5 transition-all"
                    style={{
                      background: isSelected ? 'rgba(129,140,248,0.08)' : 'transparent',
                      borderLeft: isSelected ? '3px solid #818cf8' : '3px solid transparent',
                      borderBottom: '1px solid rgba(255,255,255,0.04)',
                    }}
                  >
                    <div className="flex items-center gap-3.5">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={conv.avatar}
                        alt={conv.customer}
                        className="rounded-full object-cover flex-shrink-0"
                        style={{ width: 44, height: 44, border: '2px solid rgba(255,255,255,0.1)' }}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-sm font-semibold text-white truncate">{conv.customer}</span>
                          <span className="text-xs text-gray-600 flex-shrink-0 ml-1">{conv.timestamp}</span>
                        </div>
                        <div className="flex items-center gap-1.5 mb-1.5">
                          <span className={`${ch.cls}`}>{ch.label}</span>
                          <span className={`${STATUS_BADGE[conv.status]}`}>{conv.status}</span>
                        </div>
                        <p className="text-sm text-gray-600 truncate">{conv.lastMessage}</p>
                      </div>
                    </div>
                  </button>
                )
              })
            )}
          </div>
        </div>
      </div>

      {/* Conversation detail */}
      <div className="flex-1 flex flex-col gap-5 min-w-0">
        {/* Messages */}
        <div className="card flex-1 flex flex-col p-0 overflow-hidden">
          {selected ? (
            <>
              <div className="px-6 py-5 flex items-center justify-between flex-shrink-0" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                <div className="flex items-center gap-3.5">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={selected.avatar}
                    alt={selected.customer}
                    className="rounded-full object-cover flex-shrink-0"
                    style={{ width: 44, height: 44, border: '2px solid rgba(129,140,248,0.35)' }}
                  />
                  <div>
                    <span className="text-base font-semibold text-white">{selected.customer}</span>
                    <div className="flex items-center gap-1.5 mt-1">
                      <span className={`${(CHANNEL_BADGE[selected.channel] ?? CHANNEL_BADGE.web_form).cls}`}>
                        {(CHANNEL_BADGE[selected.channel] ?? CHANNEL_BADGE.web_form).label}
                      </span>
                    </div>
                  </div>
                </div>
                <span className={`${STATUS_BADGE[selected.status]}`}>{selected.status}</span>
              </div>

              <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
                {selected.messages.length === 0 ? (
                  <p className="text-sm text-center" style={{ color: 'rgba(255,255,255,0.2)', marginTop: 32 }}>No messages to display</p>
                ) : (
                  selected.messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === 'agent' ? 'justify-end' : 'justify-start'}`}>
                      <div
                        className="max-w-[75%] px-5 py-4 rounded-2xl text-sm whitespace-pre-wrap leading-relaxed"
                        style={
                          msg.role === 'agent'
                            ? {
                                background: 'linear-gradient(135deg,rgba(124,58,237,0.8),rgba(59,130,246,0.6))',
                                color: '#f1f5f9',
                                borderBottomRightRadius: 4,
                                boxShadow: '0 0 20px rgba(139,92,246,0.2)',
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
                        <div className="text-xs mt-2 opacity-50">{msg.timestamp}</div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center flex-1">
              <MessageSquare size={40} style={{ color: 'rgba(255,255,255,0.08)', marginBottom: 14 }} />
              <p className="text-sm font-semibold" style={{ color: 'rgba(255,255,255,0.2)' }}>Select a conversation to view details or test AI agent</p>
              <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.1)' }}>Choose one from the list on the left</p>
            </div>
          )}
        </div>

        {/* Send new message */}
        <div className="card">
          <div className="flex items-center gap-3 mb-5">
            <p className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Send to AI Agent</p>
            <select
              value={channel}
              onChange={(e) => setChannel(e.target.value as typeof channel)}
              className="input-dark w-44 ml-auto"
            >
              <option value="email">Email</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="web_form">Web Form</option>
            </select>
          </div>
          <textarea
            value={newMessage}
            onChange={(e) => { if (selected) setNewMessage(e.target.value) }}
            placeholder={selected ? 'Type a message to test the AI agent…' : 'Select a conversation first'}
            rows={4}
            disabled={!selected}
            className="input-dark resize-none mb-5"
            style={{ opacity: selected ? 1 : 0.4, cursor: selected ? 'text' : 'not-allowed' }}
          />
          <div className="flex items-center gap-3">
            {selected && (
              <button
                onClick={handleSend}
                disabled={sending || !newMessage.trim()}
                className="btn-primary"
              >
                <Send size={16} />
                {sending ? 'Sending…' : 'Send Reply'}
              </button>
            )}
            <button className="btn-ghost" title="Attach file" disabled={!selected} style={{ opacity: selected ? 1 : 0.3 }}><Paperclip size={17} /></button>
            <button className="btn-ghost" title="Emoji" disabled={!selected} style={{ opacity: selected ? 1 : 0.3 }}><Smile size={17} /></button>
            {sendResult && (
              <p className="text-sm text-gray-500 flex-1 ml-1 truncate">{sendResult}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
