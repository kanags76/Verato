# Verato — Product Plan v2

> **Status:** Planning · Not yet scheduled for build
> **Builds on:** V1 MVP (Phase 1 complete — commitments, nudges, Gmail/Slack integration)
> **Design principle:** Every v2 feature must make the CoS's working week materially shorter, not just the dashboard richer.

---

## Overview

V1 proved the core loop: upload transcript → AI extracts commitments → CoS confirms → nudges fire → replies parsed. V2 closes the five gaps that prevent a CoS from going all-in on Verato as their daily operating system.

| # | Theme | One-line summary |
|---|---|---|
| 1 | **Passive Ingestion** | Eliminate manual transcript upload entirely |
| 2 | **Executive Brief** | Replace commitment lists with AI-synthesised strategic summaries |
| 3 | **Friction Detection** | Surface cross-functional blockades before they become failures |
| 4 | **Org Health Heatmap** | Aggregate people data into departmental and leadership-layer views |
| 5 | **Nudge Intelligence** | Turn owner replies into CoS decision points, not parse failures |

---

## Feature 1 — Passive Meeting Ingestion

### The Problem
V1 requires the CoS to manually download and upload transcripts (.txt, .docx, .csv). A CoS attends 15–20 meetings per week — manual drag-and-drop is not a sustainable workflow.

### Target Experience
The CoS does nothing. The moment a meeting ends, Verato has the transcript and begins extraction. Zero clicks.

### Build Options (pick one primary path)

**Path A — Google Calendar + Google Meet auto-pull (recommended first)**
- Connect the CoS's Google account (already partially wired for Gmail OAuth)
- On connect: read Google Calendar events for the org
- After each meeting that has a Google Meet link: poll Google Drive for the auto-generated transcript (Meet creates a `.vtt` file in Drive ~2 min after the call ends)
- Pull the file, create a Meeting record, kick off `process_meeting` Celery task
- No bot, no Zoom SDK — works with the existing Google OAuth scope

**Path B — Zoom Webhook + Transcript API**
- Register a Zoom OAuth app, webhook on `recording.completed` event
- Zoom sends a webhook → Django receives it → fetches transcript via Zoom API
- Requires a Zoom Pro/Business account with cloud recording enabled
- More reliable for Zoom-heavy orgs but needs a separate OAuth app

**Path C — Calendar Bot (Recall.ai or similar)**
- Use Recall.ai or a self-hosted bot to join meetings as a silent participant
- Most powerful (works with Zoom, Meet, Teams, WebEx) but adds a third-party dependency and a monthly cost
- Recommended only if Paths A + B don't cover the org's meeting mix

### New Data Model Additions
```
CalendarConnection
    organisation → Organisation
    provider: google | zoom
    access_token, refresh_token, token_expiry
    calendar_email
    last_synced_at

CalendarEvent
    organisation → Organisation
    external_id (Google event ID / Zoom meeting ID)
    title, starts_at, ends_at
    transcript_url (Google Drive file ID or Zoom download URL)
    status: pending | fetched | processing | done | failed
    meeting → Meeting (FK, nullable — set once extraction completes)
```

### Backend Tasks
- `sync_calendar_events` — Celery beat, every 5 min: pull new events from Google Calendar API, create CalendarEvent rows
- `fetch_meeting_transcript` — fires ~3 min after event end_time: checks Drive for transcript, downloads, kicks off `process_meeting`
- Webhook receiver for Zoom: `POST /api/v1/integrations/zoom/webhook/`

### Settings Page Addition
- "Connect Google Calendar" button (reuses Google OAuth, adds `calendar.readonly` and `drive.readonly` scopes)
- List of upcoming meetings Verato will monitor
- Toggle: auto-process transcripts vs. require manual confirmation before extraction runs

---

## Feature 2 — Executive Brief (AI Context Synthesis)

### The Problem
The CEO asks: "How is the Q3 Product Launch looking?" The CoS currently has to scan 40 individual commitment rows and mentally synthesise an answer. This should take 3 seconds, not 3 minutes.

### Target Experience
The dashboard opens with a set of **Strategic Pillars** (e.g., Product Launch, Board Prep, Hiring Plan). Each pillar shows:
- An AI-generated 3-sentence executive summary ("The Product Launch is trending Yellow. Engineering is meeting 90% of commitments, but Marketing has missed 3 deadlines this week, putting the Friday timeline at risk.")
- An overall RAG status (Green / Amber / Red) computed from the commitments within it
- A count of overdue, at-risk, and on-track items underneath the summary

### New Data Model Additions
```
StrategicPillar
    organisation → Organisation
    name (e.g., "Q3 Product Launch", "Board Prep")
    description
    owner → Person (nullable — the DRI)
    target_date (nullable)
    status: active | archived
    ai_summary (text — cached, regenerated on demand)
    summary_generated_at

CommitmentPillarLink (M2M through table)
    commitment → Commitment
    pillar → StrategicPillar
    assigned_by: auto | manual
    confidence: float (for auto-assigned links)
```

### How Pillars Get Populated
1. **Manual** — CoS creates a Pillar in the dashboard, drags commitments into it (or bulk-assigns by tag/owner/date range)
2. **AI-assisted** — When a meeting is processed, Gemini tries to match each commitment to an existing Pillar based on topic and keyword proximity. CoS confirms or rejects the auto-assignment in a review queue.

### AI Summary Generation
- Celery task `regenerate_pillar_summary` — runs after any commitment status changes within the pillar
- Prompt (stored in DB Prompts table): given the pillar name, owner, target date, and a structured list of all commitments with their status/due date/owner, produce a 3-sentence executive summary in plain English, then a one-word RAG status.
- Summary is cached in `StrategicPillar.ai_summary`; stale if not regenerated in the last 2 hours

### Dashboard Changes
- New top section: "Strategic Pillars" with card-per-pillar view, RAG badge, summary, and drill-down
- Existing commitment list view remains — now filterable by pillar
- "Unassigned" bucket for commitments not yet linked to any pillar

---

## Feature 3 — Friction & Blockade Detection

### The Problem
A CoS needs to know *why* something is slipping before it actually fails. A status of "pushing to next week" is useless without knowing whether it's because the owner is overloaded, waiting on someone else, or just disorganised. These are three very different interventions.

### Target Experience
When Verato parses a nudge reply, it doesn't just extract a new date. It reads for signals:
- **Cross-functional blockade**: "I'm waiting on John's team to give me the API keys"
- **Resource constraint**: "I don't have enough dev bandwidth until the sprint ends"
- **Scope creep**: "The requirements changed again after the design review"

Each blockade is surfaced on the dashboard as a flag the CoS must actively dismiss or act on.

### New Data Model Additions
```
FrictionSignal
    commitment → Commitment
    detected_at
    signal_type: cross_functional_blockade | resource_constraint | scope_creep | dependency | unknown
    blocker_person → Person (nullable — auto-resolved from reply text if named)
    blocker_team (text, nullable)
    raw_excerpt (the sentence(s) from the reply that triggered detection)
    ai_summary (1-sentence human-readable flag)
    status: open | acknowledged | resolved
    resolved_by → User (nullable)
    resolved_at (nullable)
```

### Detection Flow
1. Gmail/Slack reply comes in and is parsed by the existing `parse_reply` flow
2. After extracting status/date, a second Gemini call runs: "Does this reply indicate a dependency on another person, team, or resource outside the owner's control? If so, identify the type, name the blocker if mentioned, and write a one-sentence flag."
3. If a blockade is detected: create `FrictionSignal`, mark commitment with a `BLOCKED` status flag (new status — add to state machine), send a push notification to the CoS

### Dashboard Changes
- New "Friction Points" section between dashboard header and pillar cards
- Each `FrictionSignal` row: commitment name, owner, blocker (if known), CoS action buttons: **Escalate to Blocker**, **Acknowledge**, **Resolve**
- "Escalate to Blocker" pre-composes a nudge to the blocker person (not the commitment owner) and logs it

### Prompt Addition (DB Prompts table)
```
key: friction_detection
```
Prompt instructs Gemini to return structured JSON: `{is_blocked: bool, signal_type: str, blocker_name: str|null, blocker_team: str|null, summary: str}`

---

## Feature 4 — Organizational Health Heatmap

### The Problem
V1 tracks delivery rate per person. A CoS thinks in terms of teams, departments, and leadership layers — not individual rows. They want to know: "Is Sales a bottleneck this quarter? Is my VP of Product a chronic under-estimator?"

### Target Experience

**Departmental Health Matrix**
A heatmap grid: departments on the Y axis, time periods (last 2 weeks, last month, last quarter) on the X axis. Each cell is colour-coded by commitment delivery rate. One click drills into the department's commitment list.

**Commitment Debt Tracker**
Per person: the average number of days by which they extend deadlines. If someone consistently misses by exactly 2 days every week, Verato flags them as a "chronic under-estimator". This surfaces as a callout on their Person detail page and in the Org Health view.

### New Data Model Additions
```
Department
    organisation → Organisation
    name
    head → Person (nullable)

Person.department → Department (FK, nullable — add to existing Person model)

PersonHealthSnapshot (computed, regenerated weekly by Celery task)
    person → Person
    period_start, period_end
    commitments_total
    commitments_on_time
    commitments_extended
    average_days_extended (float)
    delivery_rate (float — 0.0–1.0)
    is_chronic_under_estimator (bool — true if avg extension > 1.5 days over 4+ periods)

DepartmentHealthSnapshot (computed from PersonHealthSnapshot rows)
    department → Department
    period_start, period_end
    delivery_rate (float)
    total_commitments
    total_blocked (FrictionSignal count within dept)
```

### Celery Tasks
- `compute_person_health_snapshots` — weekly, recomputes for all persons with ≥3 commitments in the period
- `compute_department_health_snapshots` — runs after person snapshot task, aggregates up

### People Page Changes
- Add Department column and filter
- Per-person: show delivery trend sparkline (last 6 periods), average days extended, chronic under-estimator badge if flagged
- "Manage Departments" view: create departments, assign people, set department head

### Dashboard Changes
- New "Org Health" panel (collapsible): heatmap grid with department rows and time-period columns
- Clicking a cell filters the commitment list to that department + period

---

## Feature 5 — Bidirectional Nudge Intelligence

### The Problem
V1 parses simple replies: "done" → mark resolved; "next week" → extend by 7 days. A real reply often contains a paragraph of context, a negotiation, or a blocker explanation — all of which currently either fail to parse or get silently ignored.

### Target Experience
Every nudge reply that can't be auto-resolved lands in a **CoS Review Queue** on the dashboard. Verato presents:
- The full reply text
- Gemini's summary of what the owner is saying ("Sarah says the slides are blocked on updated financial data from Finance. She's requesting a 3-day extension.")
- The history of this commitment (prior nudges, prior extensions, prior replies)
- Two action buttons: **Approve Extension** (and optionally update deadline) or **Send Escalation Nudge**
- One optional free-text override for the CoS to send a custom reply

### New Data Model Additions
```
NudgeReply
    nudge_log → NudgeLog (FK)
    received_at
    raw_text
    channel: gmail | slack
    parsed_status: resolved | extended | blocked | unclear | auto_handled
    gemini_summary (text — Gemini's plain-English interpretation)
    extension_days_requested (int, nullable — if Gemini detects an extension request)
    review_required (bool — true if auto-resolution not possible)
    reviewed_by → User (nullable)
    reviewed_at (nullable)
    review_action: approve_extension | send_escalation | custom_reply | dismissed (nullable)
    custom_reply_text (text, nullable)
```

### Reply Processing Flow
```
Incoming reply (Gmail poll or Slack event)
    │
    ├── Step 1: Gemini call #1 — existing parse_reply prompt
    │       → extracts: intent (done/extend/blocked/unclear), new_date, raw_status
    │
    ├── Step 2 (new): Gemini call #2 — nudge_intelligence prompt
    │       → produces: plain-English summary, extension_days_requested, review_required flag
    │
    ├── If auto-resolvable (done, simple extension with clear date):
    │       → update Commitment as today (auto_handle), log NudgeReply(review_required=False)
    │
    └── If review required (blocked, unclear, complex negotiation):
            → create NudgeReply(review_required=True)
            → push notification to CoS: "Sarah replied to the Q3 slides nudge — review needed"
            → commitment status → PENDING_REVIEW (new status)
```

### Dashboard Changes
- New **Review Queue** badge on the top nav (count of open `NudgeReply` rows requiring review)
- Review Queue page: one card per pending reply, all context visible, action buttons inline
- Resolving a card: fires the chosen action (updates commitment, optionally sends reply via Gmail/Slack), marks `NudgeReply.reviewed_at`

### Prompt Addition (DB Prompts table)
```
key: nudge_intelligence
```
Prompt instructs Gemini to return structured JSON:
`{summary: str, extension_days_requested: int|null, review_required: bool, reason: str}`

---

## Cross-Cutting Changes

### State Machine Additions (Commitment.status)
V2 adds two new statuses:
- `BLOCKED` — FrictionSignal detected; commitment is waiting on an external dependency
- `PENDING_REVIEW` — NudgeReply requires CoS action before status can advance

Both must be added to the commitment lifecycle state machine with valid transitions defined.

### Notifications
- Push/in-app notification layer: real-time alerts for new FrictionSignals and NudgeReply review requests
- Initially implemented as Django Channels or a simple polling endpoint (not full WebSocket) — upgrade path to WebSocket in V3

### Prompt Management
All new Gemini prompts stored in the `apps.prompts` DB table with keys:
- `friction_detection`
- `nudge_intelligence`
- `pillar_assignment` (for auto-assigning commitments to Strategic Pillars)
- `pillar_summary` (for generating executive summaries)

---

## Build Sequence

V2 features are independent enough to ship incrementally. Recommended order:

| Sprint | Feature | Rationale |
|---|---|---|
| Sprint 1 | **Feature 5 — Nudge Intelligence** | Builds directly on existing reply parsing; no new integrations; immediate CoS value |
| Sprint 2 | **Feature 3 — Friction Detection** | Adds one Gemini call to existing reply flow; new FrictionSignal model; small surface area |
| Sprint 3 | **Feature 1 — Passive Ingestion (Google Meet path)** | Highest CoS impact; reuses Google OAuth already wired; removes biggest daily friction |
| Sprint 4 | **Feature 4 — Org Health Heatmap** | Builds on existing Person model; no new integrations; analytical, not operational |
| Sprint 5 | **Feature 2 — Executive Brief** | Most complex (new model, AI synthesis, UI redesign); deliver last so it sits on top of clean data |

---

## Dependencies and Risks

| Risk | Mitigation |
|---|---|
| Google Meet transcript availability — Meet only creates Drive transcripts if the host enables "Transcripts" in Workspace admin | Document as a prerequisite; detect missing transcript and surface a manual upload fallback |
| Gemini cost increase — V2 adds up to 3 Gemini calls per reply | Batch calls where possible; cache Pillar summaries aggressively; set per-org daily token budget |
| FrictionSignal false positive rate — Gemini may over-flag ordinary delays as blockades | Add a confidence threshold; below threshold, log signal but don't surface on dashboard |
| CoS review queue fatigue — if too many replies land in review, CoS ignores it | Default to auto-handling anything with a clear date; only escalate genuinely ambiguous replies |

---

## What V2 Does Not Include

- **Native mobile app** — web-responsive is sufficient for V2; mobile app is V3
- **Zoom path for passive ingestion** — Zoom webhook approach is a Sprint 3 extension, not the primary path
- **Teams / WebEx integration** — deferred to V3 unless beta feedback shows these are the dominant meeting tools
- **Full pgvector semantic search** — commitment debt and pattern detection uses snapshot tables in V2, not embeddings; embeddings are V3

---

*Last updated: 2026-05-23*
