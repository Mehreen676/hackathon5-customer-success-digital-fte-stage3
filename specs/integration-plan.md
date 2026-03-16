# Integration Plan — Customer Success Digital FTE

**Author:** Mehreen Asghar
**Stage:** 3 (implemented)

---

## Implemented Integrations (Stage 3)

### 1. Gmail Integration

**Status:** ✅ Implemented (MOCK mode by default, live mode with credentials)

**Files:**
- `src/integrations/gmail_client.py` — `GmailClient` wrapping Google Gmail API
- `src/webhooks/gmail_webhook.py` — Pub/Sub push notification parser
- `src/api/webhooks.py` — `POST /webhooks/gmail` endpoint

**Flow:**
```
Gmail mailbox
    ↓ users.watch() (configured once)
Google Cloud Pub/Sub topic
    ↓ push subscription
POST /webhooks/gmail  ← GmailPubSubPayload (JSON)
    ↓ parse_pubsub_notification()
    ↓ gmail_client.list_history() → gmail_client.fetch_message()
    ↓ gmail_handler.normalize()
    ↓ run_agent() → AI workflow
    ↓ gmail_client.send_reply()  (live mode only)
    ↓ WebhookAck { received, ticket_ref, escalated, mode }
```

**Credentials required for live mode:**
```bash
GMAIL_CREDENTIALS_PATH=/path/to/service_account_key.json
GMAIL_USER_EMAIL=support@nexora.io
GMAIL_DELEGATED_EMAIL=support@nexora.io  # optional, defaults to user email
```

**Without credentials:** operates in MOCK mode — logs all operations,
returns stub email data, no Google API calls made.

**Setup steps:**
1. Enable Gmail API in Google Cloud Console
2. Create a Service Account with domain-wide delegation
3. Grant the Gmail API OAuth2 scope in Google Workspace Admin
4. Create Pub/Sub topic and push subscription pointing to `/webhooks/gmail`
5. Call `users.watch()` on the mailbox to start receiving events

---

### 2. Twilio WhatsApp Integration

**Status:** ✅ Implemented (MOCK mode by default, live mode with credentials)

**Files:**
- `src/integrations/twilio_client.py` — `TwilioClient` wrapping Twilio REST API
- `src/webhooks/whatsapp_webhook.py` — Twilio form payload parser + signature validation
- `src/api/webhooks.py` — `POST /webhooks/whatsapp` endpoint

**Flow:**
```
Customer sends WhatsApp message
    ↓
Twilio receives message
    ↓ form-encoded HTTP POST
POST /webhooks/whatsapp  ← standard Twilio fields
    ↓ validate_twilio_signature() (skipped without TWILIO_AUTH_TOKEN)
    ↓ parse_twilio_webhook()
    ↓ whatsapp_handler.normalize()
    ↓ run_agent() → AI workflow
    ↓ twilio_client.send_whatsapp()  (live mode only)
    ↓ WebhookAck { received, ticket_ref, message_sid, escalated, mode }
```

**Credentials required for live mode:**
```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

**Without credentials:** operates in MOCK mode.

**Setup steps:**
1. Create a Twilio account (free trial available)
2. Join the WhatsApp sandbox or provision a WhatsApp sender
3. Set the webhook URL to `https://your-host/webhooks/whatsapp` (HTTP POST)
4. Set env vars as above

**Signature validation:**
Set `TWILIO_AUTH_TOKEN` to enable X-Twilio-Signature verification.
Install `twilio` package (`pip install twilio`) for validator support.

---

### 3. Web Support Form

**Status:** ✅ Implemented

**Files:**
- `frontend/src/app/support/page.tsx` — Public-facing support page
- `frontend/src/components/SupportForm.tsx` — Form with validation
- `frontend/src/components/TicketStatusLookup.tsx` — Ticket lookup by reference

**Backend endpoints:**
- `POST /support/submit` — same pipeline as `/support/webform`, user-facing name
- `GET  /support/ticket/{ticket_ref}` — returns status, latest response, customer info

**Frontend flow:**
```
User visits /support
    ↓ fills in name, email, subject, message
    ↓ client-side validation (required fields, email format, min length)
    ↓ POST /api/backend/support/submit
    ↓ success: show ticket_ref + agent response
    ↓ user saves TKT-XXXXXXXX reference

Later:
    ↓ user enters TKT-XXXXXXXX in TicketStatusLookup
    ↓ GET /api/backend/support/ticket/TKT-XXXXXXXX
    ↓ shows status, priority, channel, latest_response
```

---

### 4. LLM Response Generation

**Status:** ✅ Implemented (Stage 3 core)

**Files:** `src/llm/` — multi-provider client (Claude / GPT-4o / Gemini)

See `specs/ai-reasoning-design.md` for full documentation.

---

## Webhook Endpoint Reference

| Endpoint | Method | Content-Type | Caller |
|----------|--------|--------------|--------|
| `/webhooks/gmail` | POST | application/json | Google Cloud Pub/Sub |
| `/webhooks/whatsapp` | POST | application/x-www-form-urlencoded | Twilio |
| `/support/submit` | POST | application/json | Frontend support form |
| `/support/ticket/{ref}` | GET | — | Frontend / customer |

---

## Environment Variables Summary

| Variable | Required for | Description |
|----------|-------------|-------------|
| `GMAIL_CREDENTIALS_PATH` | Gmail live mode | Path to service account JSON |
| `GMAIL_USER_EMAIL` | Gmail live mode | Mailbox to send from |
| `GMAIL_DELEGATED_EMAIL` | Gmail live mode | Optional delegation target |
| `TWILIO_ACCOUNT_SID` | WhatsApp live mode | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | WhatsApp live mode + signature validation | Twilio auth token |
| `TWILIO_WHATSAPP_FROM` | WhatsApp live mode | Sender number with `whatsapp:` prefix |
| `ANTHROPIC_API_KEY` | LLM live mode | Claude API key |
| `OPENAI_API_KEY` | LLM live mode | OpenAI API key |
| `GEMINI_API_KEY` | LLM live mode | Google Gemini API key |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Gmail OAuth token expiry | Medium | Medium | Service account with domain delegation (no token expiry) |
| Twilio delivery failure | Low | Medium | Retry queue in `workers/retry_worker.py` |
| Invalid Pub/Sub signature | Low | Low | Google Pub/Sub does not sign payloads by default |
| Twilio webhook spoofing | Medium | Medium | X-Twilio-Signature validation (set `TWILIO_AUTH_TOKEN`) |
| Claude API rate limits | Medium | High | 3-tier fallback: KB → LLM → rule-based |
| Database contention | Low | Low | SQLAlchemy connection pool + per-request sessions |

---

## Optional Dependencies

These packages are NOT in `requirements.txt` by default to keep the base
install lightweight. Install them to enable live mode for each integration:

```bash
# Gmail API
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

# Twilio WhatsApp
pip install twilio

# Kafka (event streaming)
pip install confluent-kafka
```

Without any of these, the system runs fully in mock/fallback mode.
