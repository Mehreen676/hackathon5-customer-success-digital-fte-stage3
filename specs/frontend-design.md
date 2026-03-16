# Frontend Design — Nexora Customer Success Dashboard (Stage 3)

**Framework:** Next.js 14 (App Router)
**Language:** TypeScript
**Styling:** Tailwind CSS
**Port:** 3000
**Proxy:** `/api/backend/*` → `http://localhost:8000/*`

---

## Overview

The Stage 3 frontend is a lightweight monitoring and testing dashboard for the Nexora Customer Success AI agent. It communicates with the FastAPI backend via Next.js API rewrites (no CORS issues in development).

---

## Component Architecture

```
frontend/
├── src/
│   ├── app/
│   │   ├── globals.css          ← Tailwind base + custom CSS variables
│   │   ├── layout.tsx           ← Root HTML layout, Inter font
│   │   └── page.tsx             ← Main dashboard (section router)
│   ├── components/
│   │   ├── Sidebar.tsx          ← Left navigation sidebar
│   │   ├── Header.tsx           ← Top bar with status indicator
│   │   ├── ConversationPanel.tsx← Conversation viewer + message composer
│   │   ├── TicketPanel.tsx      ← Ticket list with filter tabs
│   │   ├── AnalyticsPanel.tsx   ← KPI cards + bar charts
│   │   └── ApiTesterPanel.tsx   ← Interactive API request builder
│   └── lib/
│       └── api.ts               ← Typed fetch client
├── package.json
├── next.config.mjs              ← Proxy rewrite rules
├── tailwind.config.ts
├── tsconfig.json
└── .env.local                   ← NEXT_PUBLIC_API_URL
```

---

## Page Layout

```
┌─────────────┬──────────────────────────────────────────────────────┐
│             │  Header: Page title  [Stage 3] [● Backend Online] [↺] │
│  Sidebar    ├──────────────────────────────────────────────────────┤
│             │                                                        │
│  🏠 Dashboard│              Active Panel Content                     │
│  💬 Conversations│                                                   │
│  🎫 Tickets  │                                                        │
│  📊 Analytics│                                                        │
│  🔧 API Tester│                                                       │
│  ⚙️ Settings  │                                                        │
│             │                                                        │
│  v3.0.0     │                                                        │
│  Claude AI  │                                                        │
└─────────────┴──────────────────────────────────────────────────────┘
```

---

## API Integration Points

| Component | Endpoint | Method | Purpose |
|-----------|----------|--------|---------|
| `Header` | `/health` | GET | Backend online/offline status polling (30s interval) |
| `ConversationPanel` | `/support/message` | POST | Send test message to AI agent |
| `ApiTesterPanel` | `/support/gmail` | POST | Test Email channel |
| `ApiTesterPanel` | `/support/whatsapp` | POST | Test WhatsApp channel |
| `ApiTesterPanel` | `/support/webform` | POST | Test Web Form channel |
| `ApiTesterPanel` | `/support/message` | POST | Test Generic channel |
| `AnalyticsPanel` | `/analytics/summary` | GET | KPI metrics fetch |
| `AnalyticsPanel` | `/analytics/recent` | GET | Recent interactions |

---

## State Management

No external state library (Redux, Zustand, etc.). Uses:

- `useState` — local component state (selected conversation, active tab, response data)
- `useEffect` — data fetching on mount, health check interval
- `useCallback` — memoised refresh function for health checks
- Props drilling — kept minimal; each panel is self-contained

---

## Navigation Sections

| Section ID | Label | Component | Description |
|------------|-------|-----------|-------------|
| `dashboard` | Dashboard | Inline in page.tsx | Overview with architecture summary |
| `conversations` | Conversations | ConversationPanel | Viewer + composer |
| `tickets` | Tickets | TicketPanel | Filterable ticket list |
| `analytics` | Analytics | AnalyticsPanel | KPIs + charts |
| `api-tester` | API Tester | ApiTesterPanel | Request builder |
| `settings` | Settings | Inline in page.tsx | Config reference |

---

## Mock Data Strategy

All panels include realistic mock data so the dashboard renders without the backend running:

- `ConversationPanel`: 3 mock conversations (active, escalated, resolved)
- `TicketPanel`: 6 mock tickets spanning all priorities and statuses
- `AnalyticsPanel`: demo data from `api.ts` fallback (1,247 interactions)
- `ApiTesterPanel`: pre-filled request bodies for all 4 channels

When the backend IS running, live data replaces the mock data.

---

## Responsive Design

- Mobile: panels stack vertically
- Tablet: sidebar collapses to icon strip *(future enhancement)*
- Desktop: full sidebar + main content layout
- Breakpoints: Tailwind `sm` (640px), `lg` (1024px)

---

## Development Setup

```bash
# Prerequisites: Node.js 18+

cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
# → http://localhost:3000

# Build for production
npm run build
npm start
```

---

## Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL |

Set in `frontend/.env.local` (already created).

---

## Build Output

```
frontend/.next/          ← compiled output
frontend/node_modules/   ← dependencies (gitignored)
```

---

## Known Limitations

1. No real-time WebSocket feed — analytics refresh on navigation only
2. Ticket/conversation data is mock only — no backend CRUD endpoints for these (Stage 4)
3. No authentication — open access in development
4. No dark mode — light theme only
