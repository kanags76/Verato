# Verato — Phase 2 Frontend Build Plan
## Next.js · TypeScript · Dark-first design system · All 9 prototype screens

> **Status:** Phase 1 backend complete (310 tests passing). This plan converts the working
> HTML prototype (`Design/Verato/Verato.html`) into a production Next.js app that calls
> the real Django API.
>
> **Prototype reference:** `Design/Verato/` — 9 screens already designed, fully responsive,
> dark/light theme. Port these; do not redesign.

---

## What we have going in

| Asset | Location | What it gives us |
|---|---|---|
| Working prototype | `Design/Verato/Verato.html` | All screens, interactions, and responsive behaviour |
| Design tokens | `components.jsx` → `T` object | Exact colours, typography, spacing |
| Screen components | `screens-auth.jsx`, `screens-dashboard.jsx`, `screens-meetings.jsx` | Component structure + all UI states |
| Mock data | `data.js` | API response shapes to match |
| Mobile design | `responsive.jsx` | Breakpoint (768px), mobile nav patterns, swipe-review UX |
| API docs | `localhost:8000/api/schema/ui/` | Full Swagger — all endpoints ready |

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Framework | **Next.js 14 (App Router)** | File-based routing, server components, image optimisation |
| Language | **TypeScript** | Type safety against API responses |
| Styling | **Tailwind CSS + CSS variables** | Port `T` tokens to CSS vars; use Tailwind utilities |
| Server state | **TanStack Query (React Query v5)** | Caching, refetch, loading/error states with minimal code |
| Forms | **React Hook Form + Zod** | Inline validation matching prototype UX |
| HTTP | **Axios** | Interceptor-based JWT injection + refresh |
| Auth | **Custom JWT (localStorage → httpOnly cookie via Next.js middleware)** | No NextAuth — we control the flow |
| Testing | **Vitest + React Testing Library** | Unit + component tests |
| E2E | **Playwright** | End-to-end happy paths |
| Deploy | **Vercel** (local→prod) | Zero-config Next.js; free tier for design partners |

---

## Design system port (do once — Week 1)

The prototype `T` object in `components.jsx` maps directly to CSS variables:

```css
/* app/globals.css */
:root[data-theme="dark"] {
  --bg:           #0c0c0f;
  --surface:      #13131a;
  --panel:        #1a1a24;
  --border:       #23232e;
  --border-faint: #1c1c26;
  --text:         #e6e6f0;
  --text-mid:     #9a9aae;
  --text-faint:   #6a6a82;
  --accent:       #7c6af7;
  --rose:         #f87171;
  --amber:        #fbbf24;
  --sage:         #4ade80;
}
:root[data-theme="light"] { /* LIGHT_THEME values from responsive.jsx */ }
```

**Fonts (load via `next/font`):**
- Plus Jakarta Sans 400/500/600/700/800 — UI
- JetBrains Mono 400/600/700 — numbers, status chips, timestamps

**Breakpoint:** single `768px` — same as prototype. `useMediaQuery(768)` hook.

**Shared components to build first** (all exist in prototype, just port):
- `Button` (primary / secondary / danger variants)
- `Badge` (status + priority variants)
- `Avatar` (initials-based, coloured by name hash)
- `Sidebar` (desktop) + `Drawer` (mobile hamburger)
- `BottomNav` (mobile alternative to drawer)
- `PriorityBar` (3-segment signal icon — HIGH/MED/LOW)
- `RiskDot` (rose/amber/sage circle)
- `TagPill` (clickable, dismissible variant)
- `ConfidenceBar`

---

## Project structure

```
frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   ├── register/
│   │   │   ├── page.tsx               ← plan picker
│   │   │   └── form/page.tsx          ← sign-up form
│   │   └── invite/[token]/page.tsx    ← accept invite
│   ├── (app)/                         ← authenticated shell (sidebar)
│   │   ├── layout.tsx                 ← Sidebar + auth gate
│   │   ├── dashboard/page.tsx
│   │   ├── commitments/[id]/page.tsx
│   │   ├── upload/page.tsx
│   │   ├── review/[meetingId]/page.tsx
│   │   ├── meetings/page.tsx
│   │   ├── people/page.tsx
│   │   └── settings/
│   │       ├── page.tsx               ← redirects to /settings/org
│   │       ├── org/page.tsx
│   │       ├── slack/page.tsx
│   │       └── team/page.tsx
│   ├── onboarding/
│   │   ├── slack/page.tsx
│   │   ├── import/page.tsx
│   │   └── done/page.tsx
│   ├── layout.tsx                     ← root (theme provider, query client)
│   └── globals.css
├── components/
│   ├── ui/                            ← Button, Badge, Avatar, etc.
│   ├── commitment/                    ← CommitmentRow, CommitmentDetail, ActionBar
│   ├── review/                        ← ReviewRow, ReviewCard (mobile swipe)
│   └── layout/                        ← Sidebar, Drawer, BottomNav, TopBar
├── lib/
│   ├── api/                           ← axios instance + typed API functions
│   │   ├── client.ts                  ← axios + JWT interceptor
│   │   ├── auth.ts
│   │   ├── commitments.ts
│   │   ├── meetings.ts
│   │   ├── people.ts
│   │   ├── tags.ts
│   │   └── slack.ts
│   ├── hooks/                         ← React Query wrappers
│   │   ├── useCommitments.ts
│   │   ├── useDashboardStats.ts
│   │   └── ...
│   ├── auth.ts                        ← token storage, refresh logic
│   ├── theme.ts                       ← theme provider + useTheme
│   └── types.ts                       ← API response types
├── middleware.ts                       ← redirect unauthenticated → /login
└── public/
```

---

## API client pattern

Every API module follows the same shape so the frontend never calls `fetch` or `axios` directly:

```ts
// lib/api/commitments.ts
export const getCommitments = (params: CommitmentsParams) =>
  client.get<CommitmentsResponse>('/commitments/', { params });

export const patchCommitment = (id: string, data: Partial<CommitmentPatch>) =>
  client.patch<Commitment>(`/commitments/${id}/`, data);

export const bulkConfirm = (meetingId?: string, minConfidence?: number) =>
  client.post('/commitments/bulk-confirm/', { meeting: meetingId, min_confidence: minConfidence });
```

```ts
// lib/hooks/useCommitments.ts
export const useCommitments = (params: CommitmentsParams) =>
  useQuery({ queryKey: ['commitments', params], queryFn: () => getCommitments(params) });
```

---

## Backend additions required before building (minor)

Three small endpoints needed for the frontend that aren't in Phase 1:

| Endpoint | Method | Why needed | Screen |
|---|---|---|---|
| `/api/v1/auth/invitations/` | GET | List pending invites for the org | Settings → Team tab |
| `/api/v1/commitments/bulk-confirm/` | POST | Add `meeting` filter param so review can confirm just this meeting's items | Extraction Review |
| Meeting serializer | — | Add `commitment_count` + `pending_count` computed fields | Meetings list |

**These are the only 3 backend changes.** Build them at the start of Week 1 (30 min total).

---

## User story → screen mapping

| Epic | User Story | Screen | Week |
|---|---|---|---|
| 1 | US-1.1 Plan picker | `/register` | 2 |
| 1 | US-1.2 Sign-up form | `/register/form` | 2 |
| 1 | US-1.3 Connect Slack | `/onboarding/slack` | 2 |
| 1 | US-1.4 Import tracker | `/onboarding/import` | 2 |
| 2 | US-2.1 Stat cards | `/dashboard` | 3 |
| 2 | US-2.2 Status tabs | `/dashboard` | 3 |
| 2 | US-2.3 Priority chips | `/dashboard` | 3 |
| 2 | US-2.4 Tag filter | `/dashboard` | 3 |
| 2 | US-2.5 Commitment rows | `/dashboard` | 3 |
| 3 | US-3.1 Commitment detail | `/commitments/[id]` | 4 |
| 3 | US-3.2 Edit priority | `/commitments/[id]` | 4 |
| 3 | US-3.3 Add/remove tags | `/commitments/[id]` | 4 |
| 3 | US-3.4 Action buttons | `/commitments/[id]` | 4 |
| 3 | US-3.5 Audit trail | `/commitments/[id]` | 4 |
| 4 | US-4.1 Upload transcript | `/upload` | 5 |
| 4 | US-4.2 Extraction review | `/review/[meetingId]` | 5 |
| 4 | US-4.3 Bulk-confirm | `/review/[meetingId]` | 5 |
| 4 | US-4.4 Edit before confirm | `/review/[meetingId]` | 5 |
| 6 | US-6.1 Invite colleagues | `/settings/team` | 6 |
| 6 | US-6.2 Manage Slack | `/settings/slack` | 6 |
| 6 | US-6.3 Confidence threshold | `/settings/org` | 6 |
| 7 | US-7.1 People page | `/people` | 6 |
| 7 | US-7.2 Meetings list | `/meetings` | 6 |

---

## Week-by-week plan

---

### Week 1 — Foundation

**Goal:** Next.js project boots, design system works, auth round-trip works, protected routes gate correctly.

**Backend (30 min):**
- Add `commitment_count` + `pending_count` to `MeetingSerializer`
- Add `GET /api/v1/auth/invitations/` — org admin sees pending invites
- Add `meeting` filter param to `POST /commitments/bulk-confirm/`

**Frontend:**
1. Scaffold: `npx create-next-app@latest frontend --typescript --tailwind --app`
2. CSS variables from design system (`globals.css`)
3. Next/Font: Plus Jakarta Sans + JetBrains Mono
4. Axios instance: base URL, JWT header injection, 401 → refresh → retry interceptor
5. `ThemeProvider` — reads `localStorage`, applies `data-theme` to `<html>`
6. `middleware.ts` — redirect unauthenticated requests to `/login`
7. Build all shared UI components (Button, Badge, Avatar, Sidebar, etc.)
8. **Login page** — form → `POST /auth/token/` → store tokens → redirect to `/dashboard`
9. **Accept invite page** — reads `?token=`, validates → `GET /auth/invite/validate/` → form → `POST /auth/invite/accept/` → redirect to `/onboarding/slack`

**Done when:**
- `npm run dev` runs clean
- Login → Dashboard redirect works
- Invalid token → back to login
- Theme toggle switches dark/light

---

### Week 2 — Sign-up & Onboarding

**Goal:** A new user can create an org, connect Slack, and import their existing tracker without help.

**Screens:** Plan picker → Sign-up form → Onboarding (Slack → Import → Done)

**Plan picker** (`/register`):
- Two cards: Individual + Team, "RECOMMENDED" badge on Team
- Click carries `plan` into the form

**Sign-up form** (`/register/form`):
- Fields: name, work email, password, organisation name
- Inline Zod validation (email format, password ≥ 8 chars)
- Submit → `POST /auth/register/` → store tokens → check `is_first_login` → route to `/onboarding/slack`
- Back button returns to plan picker preserving plan

**Onboarding — Slack** (`/onboarding/slack`):
- Step 1/4 indicator
- Explains 3 scopes in plain English
- "Add to Slack" → `GET /slack/oauth/start/` (browser redirect)
- Skip link routes to `/onboarding/import`
- After OAuth callback: `GET /slack/status/` → if connected, show green success → "Next →"

**Onboarding — Import** (`/onboarding/import`):
- Drag-drop zone (.csv .xlsx .docx .txt .md) OR "paste text" textarea
- `POST /meetings/import/` with file → 202 → poll `GET /meetings/{id}/status/`
- Progress spinner while polling
- On complete → route to `/review/{meetingId}` with `source=import`
- "I'll start fresh" skip → `/dashboard`

**Onboarding — Done** (`/onboarding/done`):
- Brief success card: "You're set up. Here's your dashboard."
- Single CTA → `/dashboard`

---

### Week 3 — Dashboard (Command Centre)

**Goal:** The CoS opens the app, sees everything that needs attention in 10 seconds, and can filter to exactly what they want.

**Screen:** `/dashboard`

**Stat row** (US-2.1):
- 4 cards: Overdue (rose) · At Risk (amber) · On Track (sage) · Total Active (neutral)
- Data from `GET /dashboard/`
- Clicking a card sets the active status filter

**Commitment list** (US-2.2 to 2.5):
- Status tab row: All Active · Needs Attention · At Risk · On Track · Delivered
- Priority chips (P1 / P2 / P3) — multi-select, right-aligned — filter composes with tabs
- Tag filter banner — appears when tag pill is clicked anywhere in the list
- Each row: priority bar · risk dot · title · source meeting · owner avatar+name · deadline · status badge
- Hover: subtle background lift
- "Nudge sent N times" meta when `escalations.length > 0`
- Overdue items: badge overrides to OVERDUE regardless of stored status
- Empty state: "All clear — nothing here" with check icon
- Sort: `ordering=deadline,-risk_score` (matches API default)

**Header** (US-2.6):
- "Upload transcript" (primary) + "Import" (secondary) buttons top-right
- Both open the respective routes

**Data:**
```
GET /commitments/?status=<>&priority=<>&tags__label=<>&ordering=deadline,-risk_score
GET /dashboard/
```

**Done when:** filtering by any combination of status + priority + tag works live without page reload.

---

### Week 4 — Commitment Detail

**Goal:** CoS can open any commitment and take any action — nudge, deliver, defer, tag — from one screen.

**Screen:** `/commitments/[id]`

**Header:** Title · Status badge (large) · Back link · Priority picker (inline segmented control)

**Meta grid** (4 cells):
- Owner: avatar + name + role
- Deadline: date + relative countdown ("3 days overdue" in rose)
- Source: meeting title + date (links to `/meetings`)
- Confidence: progress bar + score

**Risk section:**
- Score as percentage + coloured bar
- Three formula labels: "50% deadline · 35% owner · 15% recency"

**Quote block:**
- `raw_text` in italic, accent left-border

**Tags** (US-3.3):
- Current tags as dismissible pills
- Input with autocomplete: `GET /tags/?q=<>` on keypress (debounced 200ms)
- Enter/click adds; ✕ removes; PATCH saves immediately
- New tags created on the fly (API does `get_or_create`)

**Action bar** (US-3.4):
- 4 buttons: Send Slack nudge · Mark delivered · Defer · Cancel
- Nudge: `POST /commitments/{id}/nudge/` → in-place success banner
- Deliver: `POST /commitments/{id}/resolve/` with `{outcome: "delivered"}` → status badge updates
- Defer: expands inline date picker → `POST /commitments/{id}/resolve/` with `{outcome: "deferred", new_deadline: <date>}`
- Cancel: confirmation → `POST /commitments/{id}/resolve/` with `{outcome: "cancelled"}`
- After any action: banner replaces button row, then timeline below updates

**History / Audit trail** (US-3.5):
- Right-rail card "History"
- Timeline from `escalations[]` on the commitment response
- Each event: timestamp (JetBrains Mono) · one-line description
- Owner card below: name, role, delivery rate bar

**Data:**
```
GET /commitments/{id}/
PATCH /commitments/{id}/            ← priority, tags
POST /commitments/{id}/nudge/
POST /commitments/{id}/resolve/
GET /tags/?q=<>
```

---

### Week 5 — Capture (Upload + Extraction Review)

**Goal:** CoS uploads a transcript and gets to a reviewed, confirmed set of commitments in under 5 minutes.

**Upload screen** (`/upload`) (US-4.1):
- Form: meeting title · date · participants (optional, comma-separated)
- Drag-drop zone or paste textarea (monospace)
- Accepts .txt .docx .pdf .vtt .srt
- Submit disabled until title + date + (file or text) all present
- Submit → `POST /meetings/` multipart → 202 → polling loop on `GET /meetings/{id}/status/`
- Full-page spinner: "Extracting commitments… Gemini is reading your transcript."
- On `status = complete` → navigate to `/review/{meetingId}`

**Extraction Review screen** (`/review/[meetingId]`) (US-4.2 to 4.5):
- Header: meeting title · "N found · M confirmed · P pending review" counts
- Confidence legend: ≥0.80 HIGH · 0.65–0.79 REVIEW · <0.65 LOW
- "Confirm all ≥ 0.80" button → `POST /commitments/bulk-confirm/` with `{meeting: meetingId, min_confidence: 0.80}`
- Per-row data: confidence score (mono, colour) · normalised_text · owner · deadline · tags
- Per-row: green ✓ (confirm) · red ✕ (reject)
  - Confirm → `POST /commitments/{id}/confirm/` → row turns sage
  - Reject → `POST /commitments/{id}/reject/` → row fades
  - "Undo" link for any decided row
- Inline edit before confirming (US-4.4): click owner/deadline/priority/tags to edit inline, then confirm
- "Add N to tracker →" CTA (disabled until at least 1 confirmed and 0 still pending)
- On complete → navigate to `/dashboard`

**Mobile swipe review** (from `responsive.jsx`):
- Below 768px: single card stack instead of list
- Swipe right = confirm, swipe left = reject
- Buttons at bottom

---

### Week 6 — People, Meetings, Settings

**Goal:** Every screen the CoS uses beyond the daily loop is functional.

**People page** (`/people`) (US-7.1):
- `GET /persons/` with aggregate fields
- One card per person: avatar · name · role · total commitments · meeting count
- Delivery rate: bar + percentage · colour-coded (≥85% sage / 65–84% amber / <65% rose)
- Empty state for orgs with no tracked participants yet

**Meetings list** (`/meetings`) (US-7.2):
- `GET /meetings/` — columns: title · type badge · date · commitment count · pending count
- Checkmark when pending_count = 0
- Click row → `/review/{meetingId}` (shows existing commitments in review view for re-check)
- Upload + Import CTAs in header (same as dashboard)

**Settings — Org tab** (`/settings/org`) (US-6.3):
- Confidence threshold slider: 0.50 – 0.95, step 0.05, default 0.65
- Live numeric readout in JetBrains Mono
- Saves on blur/submit via `PATCH /orgs/{id}/settings/` with `{confidence_threshold}`
- Nudge timing: `nudge_hours_before` input (default 48h)
- Digest schedule: `digest_day` + `digest_hour` selectors

**Settings — Slack tab** (`/settings/slack`) (US-6.2):
- `GET /slack/status/`
- If connected: green "● Connected" pill + workspace name + "Reconnect" option
- If not: "Add to Slack" CTA → same OAuth flow as onboarding
- "Your Slack ID" field: shows linked ID or input to set it → `POST /persons/{id}/link-slack/`
- "Send test message" → `POST /slack/test-message/` → in-place success/error

**Settings — Team tab** (`/settings/team`) (US-6.1):
- Members list: name · email · role · status (Active / Pending)
- `GET /auth/invitations/` for pending invite rows
- "Invite colleague" → inline email input → `POST /auth/invite/` → row appears as PENDING
- Individual plan: invite section locked with "Upgrade to Team to add colleagues" copy

---

### Week 7 — Polish, Mobile, Testing

**Goal:** Production-ready. Design partners can use this on day one.

**Mobile pass** (responsive.jsx patterns):
- Sidebar collapses to hamburger drawer or bottom-tab nav (user preference, stored in localStorage)
- Commitment rows become stacked cards
- Extraction review becomes swipe stack
- All touch targets ≥ 44px
- Test at 375px (iPhone SE), 390px (iPhone 14), 768px (iPad)

**Error and loading states on every screen:**
- Skeleton loaders (not spinners) for lists
- Inline error banners with retry for failed mutations
- 0-item empty states with contextual copy

**Keyboard shortcuts** (US-X.3):
- J / K to move through commitment rows
- Enter to open detail
- Escape to close detail / dismiss modal
- Basic implementation only — ⌘K command palette is Phase 3

**Performance:**
- Dashboard should render under 200ms (US-X.3)
- Use `staleTime: 30_000` in React Query to avoid unnecessary refetches
- Static shell with streaming data

**Testing:**
- Vitest unit tests for: auth token logic, risk colour thresholds, date formatting helpers
- Playwright E2E: login → upload → review → confirm → dashboard (golden path)

**Deploy:**
- `vercel deploy` from `frontend/`
- Environment variables: `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` (local) / production URL (later)

---

## User stories vs API — final gap check

| User Story | API status |
|---|---|
| US-1.1 Plan picker | No API call — hard-coded plans |
| US-1.2 Sign-up form | ✅ `POST /auth/register/` + `is_first_login` |
| US-1.3 Connect Slack | ✅ `/slack/oauth/start/` + `/slack/status/` |
| US-1.4 Import tracker | ✅ `POST /meetings/import/` + polling |
| US-2.1 Stat cards | ✅ `GET /dashboard/` |
| US-2.2 Status tabs | ✅ `GET /commitments/?status=` |
| US-2.3 Priority chips | ✅ `GET /commitments/?priority=` |
| US-2.4 Tag filter | ✅ `GET /commitments/?tags__label=` + `GET /tags/` |
| US-2.5 Commitment rows | ✅ list API with embedded owner/meeting/escalations |
| US-3.1 Commitment detail | ✅ `GET /commitments/{id}/` |
| US-3.2 Edit priority | ✅ `PATCH /commitments/{id}/` with `priority` |
| US-3.3 Add/remove tags | ✅ `PATCH /commitments/{id}/` with `tags[]` + `GET /tags/?q=` |
| US-3.4 Action buttons | ✅ `/nudge/`, `/resolve/` |
| US-3.5 Audit trail | ✅ `escalations[]` embedded in detail |
| US-4.1 Upload transcript | ✅ `POST /meetings/` + `GET /meetings/{id}/status/` |
| US-4.2 Extraction review | ✅ `GET /commitments/?meeting=<id>&status=pending_review` |
| US-4.3 Bulk-confirm | 🔧 `POST /commitments/bulk-confirm/` — needs `meeting` param |
| US-4.4 Edit before confirm | ✅ `PATCH /commitments/{id}/` (edit, then confirm) |
| US-6.1 Invite colleagues | ✅ `POST /auth/invite/` · 🔧 `GET /auth/invitations/` not yet built |
| US-6.2 Manage Slack | ✅ `/slack/status/` + `/slack/test-message/` + `/persons/{id}/link-slack/` |
| US-6.3 Confidence threshold | ✅ `PATCH /orgs/{id}/settings/` |
| US-7.1 People page | ✅ `GET /persons/` with aggregate fields |
| US-7.2 Meetings list | 🔧 Meeting serializer needs `commitment_count` + `pending_count` |

---

## Out-of-scope for Phase 2 (deferred from user stories)

These are noted in the user stories as explicitly deferred:

| Story | Deferred to |
|---|---|
| Per-person quiet hours (US-5.2) | Phase 3 — needs `quiet_hours` on Person model |
| Saved views / "My Monday morning" | Phase 3 — user research first |
| Real-time WebSocket updates | Phase 3 — manual refresh is acceptable for MVP |
| ⌘K command palette | Phase 3 |
| Dependency / blocker links | Phase 3 |
| Weekly digest email designer | Phase 3 |
| Google Workspace SSO | Phase 3 |

---

## Session startup (once frontend folder exists)

```bash
# Services (same as backend)
brew services list | grep -E "postgresql|redis"

# Backend — Terminal Tab 1
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.local
python manage.py runserver          # → localhost:8000

# Frontend — Terminal Tab 2
cd ~/Documents/Programs/Verato/frontend
npm run dev                         # → localhost:3000

# Tests — Terminal Tab 3
cd ~/Documents/Programs/Verato/frontend
npm run test                        # Vitest watch

# Tab 4 — Git / shell (free)
```

**CORS:** Backend already allows `localhost:3000` (set `CORS_ALLOWED_ORIGINS` in `config/settings/local.py` if not already done).

---

## Success criteria for Phase 2

Phase 2 is done when a design partner can:

1. Sign up, connect their Slack workspace, and import their existing tracker — unassisted
2. Upload a new transcript and review / confirm extracted commitments — in under 5 minutes
3. See their dashboard every morning and know exactly what needs attention
4. Open any commitment and take the right action (nudge / defer / resolve) in one click
5. Use the app on their phone with the same feature set as desktop

**Vercel preview URL** shared with design partners after Week 7.
