# Verato — User Stories

User stories anchored in the v0.3 prototype (`Verato.html`). Each story is written from a specific persona's perspective and includes acceptance criteria mapped to UI elements you can see in the prototype.

> **Status legend** for API support:
> ✅ supported by current spec · ⚠️ partial · 🆕 new endpoint/field needed

---

## Personas

| Persona | Description | Primary screens |
|---|---|---|
| **CoS** (Chief of Staff) | Primary admin user. Owns the tracker. Reads transcripts, confirms extractions, sends nudges, reviews the dashboard daily. | All screens |
| **Owner** | Colleague who gets commitments assigned. Receives Slack DMs. May or may not log in. | Slack nudge, Detail (read-only) |
| **New user** | Visitor who hasn't signed up yet. | Sign-up flow |
| **Admin** | Same as CoS in MVP. Listed where the action is admin-gated. | Settings |

---

## Epic 1 — Sign-up & onboarding

### US-1.1 — Pick a plan
**As a** new user
**I want to** see the available plans before I create an account
**So that** I know whether I'm signing up alone or for my team

**Acceptance criteria**
- Plan picker shows two cards: Individual and Team
- "Team" is visually marked as **RECOMMENDED**
- Each card lists 4 differentiating features (logins, Slack workspaces, invites, extraction)
- Both plans show "no credit card · free for 3 months" copy
- Clicking either card carries the plan choice into the sign-up form

**API needs:** 🆕 `GET /api/v1/billing/plans/` (live plan defs) · ✅ no backend call needed for MVP if plans are hard-coded

---

### US-1.2 — Create my account
**As a** new user
**I want to** create my account in a single short form
**So that** I can start using Verato in under a minute

**Acceptance criteria**
- Form captures: name, work email, password, organisation name
- Inline validation: email format, password ≥ 8 chars
- Back button returns to plan picker (preserving plan)
- Submit shows "Creating account…" loading state then auto-advances to onboarding
- Error states are inline per-field, not in a banner

**API needs:** ✅ `POST /api/v1/auth/register/` · ⚠️ org_name + plan in payload · 🆕 `is_first_login` flag in response · 🆕 email verification endpoints

---

### US-1.3 — Connect Slack during onboarding
**As a** CoS
**I want to** connect my Slack workspace as part of onboarding
**So that** Verato can send nudges to commitment owners on my behalf

**Acceptance criteria**
- Step indicator shows position 1/4 in the onboarding journey
- Page explains *why* Slack is needed (one sentence)
- Lists the 3 scopes Verato will request (DMs, button responses, no channel access)
- "Add to Slack" CTA in Slack-purple branding
- Skippable via "Skip for now — connect later from Settings"
- Skip and connect both route forward to the Import step

**API needs:** ✅ `GET /api/v1/integrations/slack/oauth-url/` · ✅ OAuth callback · 🆕 `GET .../slack/status/` · 🆕 `POST .../slack/test-message/`

---

### US-1.4 — Import my existing tracker
**As a** CoS
**I want to** drag in my existing spreadsheet or paste my notes from another tool
**So that** Verato is useful from minute one, not week three

**Acceptance criteria**
- Drag-drop zone accepts .csv .xlsx .docx .txt .md
- Visual feedback while dragging (border + tint)
- Filename is shown after drop with a clear ✕ to remove
- "or paste text" divider with textarea fallback
- Disabled "Extract items" button until file or text present
- Skippable — "I'll start fresh"
- After extraction completes, routes to Extraction Review with `source = 'import'`

**API needs:** 🆕 `POST /api/v1/imports/` (distinct from meetings) · 🆕 `GET /api/v1/extraction-jobs/<id>/` for progress polling · 🆕 imported items have `meeting_id: null` + `import_id: <id>`

---

## Epic 2 — Daily command centre (Dashboard)

### US-2.1 — See what needs my attention right now
**As a** CoS opening Verato in the morning
**I want to** see at a glance how many things are overdue, at risk, on track
**So that** I can prioritise my day in the first 10 seconds

**Acceptance criteria**
- 4 stat cards at the top: Overdue · At Risk · On Track · Total Active
- Counts are colour-coded (rose / amber / sage / neutral)
- Clicking a stat filters the list below to that status
- Numbers use monospace type for stable alignment
- "Week of [date]" subtitle anchors the view in time

**API needs:** 🆕 `GET /api/v1/dashboard/stats/` (single aggregate) · ✅ filtered list endpoints

---

### US-2.2 — Filter commitments by status
**As a** CoS
**I want to** switch between status views with one click
**So that** I can focus on overdue items, then sweep at-risk, then check delivered

**Acceptance criteria**
- Tab row: All active · Needs attention · At risk · On track · Delivered
- Active tab is underlined in accent colour with bold text
- List below updates instantly without page reload
- Empty state shows "Nothing here — all clear" with a check icon

**API needs:** ✅ `GET /api/v1/commitments/?status=<>`

---

### US-2.3 — Filter by priority
**As a** CoS
**I want to** filter the dashboard to only P1 (or P1+P2) commitments
**So that** I can ignore noise during a busy week

**Acceptance criteria**
- Priority chips (P1, P2, P3) in the filter row, right-aligned
- Multi-select — clicking chips toggles them on/off
- Active chips have a filled background; inactive are outlined
- Filters compose with status tabs (e.g. "At risk + P1")
- A "Clear" link appears when any chip is active

**API needs:** ⚠️ `GET /api/v1/commitments/?priority=high` (filter param needs to be added) · 🆕 `priority` field on Commitment model

---

### US-2.4 — Filter by tag with one click
**As a** CoS preparing for a board meeting
**I want to** click any tag and see every commitment with that tag
**So that** I can pull together "everything tagged board prep" without typing a query

**Acceptance criteria**
- Every tag pill in every dashboard row is clickable
- Click → page filters to that tag instantly
- A banner appears below the filter row: "Filtered by tag: #pricing · clear ×"
- Banner persists across status / priority filter changes
- Clear × removes only the tag filter, not other filters

**API needs:** ⚠️ `GET /api/v1/commitments/?tag=<>` · 🆕 `GET /api/v1/tags/` for tag library + autocomplete

---

### US-2.5 — Scan commitments efficiently
**As a** CoS
**I want** each row to show the most important context without me clicking
**So that** I can triage 30 items in 60 seconds

**Acceptance criteria**
- Each row shows: priority bar, risk dot (red/amber/green), title, source meeting, owner avatar+name, deadline (formatted "30 Apr"), status badge
- Rows hover to a subtle background lift
- "Nudge sent N times" inline meta when applicable
- Overdue items auto-promote their status badge to OVERDUE regardless of stored status
- Sort: overdue first, then descending by risk score

**API needs:** ✅ commitment list with embedded owner, meeting, escalation count

---

### US-2.6 — Get to the right action fast
**As a** CoS
**I want** Upload and Import buttons in the dashboard header
**So that** I don't have to navigate away to add new content

**Acceptance criteria**
- Top-right of dashboard: secondary "Import" button + primary "Upload transcript" button
- Both icons + labels
- Upload routes to the Upload Transcript form
- Import routes to the same flow as onboarding-import (with no skip option)

**API needs:** N/A (navigation only)

---

## Epic 3 — Working a single commitment

### US-3.1 — See the full context of one commitment
**As a** CoS
**I want to** click a commitment and see every detail in one screen
**So that** I have full context before nudging the owner or deferring

**Acceptance criteria**
- Page header: title, status badge (large), back link to dashboard
- 4-cell meta grid: Owner (with avatar + role) · Deadline (with overdue countdown) · Source (meeting + date) · Confidence (bar + score)
- Risk score component: percentage, coloured progress bar, formula breakdown labels (50% deadline / 35% owner / 15% recency)
- Original quote in an italic accent-bordered block
- Tags as pills below

**API needs:** ✅ `GET /api/v1/commitments/<id>/` · 🆕 `priority` field

---

### US-3.2 — Edit priority inline
**As a** CoS
**I want to** change a commitment's priority directly on the detail screen
**So that** I don't have to navigate to a separate edit form

**Acceptance criteria**
- Priority picker is visible next to the title
- Click → inline dropdown / segmented control (HIGH / MED / LOW)
- Change persists immediately, no save button
- Dashboard reflects the new priority on next visit
- Audit trail records the change

**API needs:** ✅ `PATCH /api/v1/commitments/<id>/` with `priority` · 🆕 `priority` field on model · 🆕 history entry for priority changes

---

### US-3.3 — Add and remove tags
**As a** CoS
**I want to** add tags inline with autocomplete from my org's existing tags
**So that** taxonomy stays consistent across the team

**Acceptance criteria**
- Tag input below the meta grid
- Typing shows autocomplete suggestions ranked by org-wide usage
- Enter or click adds the tag; ✕ on each pill removes it
- New tags can be created on the fly
- Changes save instantly

**API needs:** 🆕 `GET /api/v1/tags/?q=<>` for autocomplete · ✅ `PATCH /api/v1/commitments/<id>/` with tags array

---

### US-3.4 — Take action on a commitment
**As a** CoS
**I want** clear action buttons for the four things I do most
**So that** I can resolve items in one click

**Acceptance criteria**
- Action row with 4 buttons: Send Slack nudge · Mark delivered · Defer · Cancel
- Each is colour-coded (neutral / sage / neutral / rose)
- Defer expands inline date picker rather than opening a modal
- After any action, an in-place success banner replaces the action row ("Slack nudge sent to Sarah K.")
- The action is reflected in the audit trail timeline immediately

**API needs:** ✅ `POST /api/v1/commitments/<id>/nudge/` · ✅ `PATCH .../<id>/` for status changes · ✅ history auto-appended

---

### US-3.5 — See the full audit trail
**As a** CoS
**I want to** see every event in this commitment's history
**So that** I can answer "when did we last hear from Sarah on this?"

**Acceptance criteria**
- Right-rail card titled "History"
- Vertical timeline with one dot + line per event
- Most recent at top, dot in accent colour
- Each event shows: timestamp (mono, formatted "30 Apr 09:00"), one-line note
- Owner card below history showing name, role, delivery rate bar

**API needs:** ✅ history embedded in commitment detail response · 🆕 `GET /api/v1/commitments/<id>/history/` paginated for long histories

---

## Epic 4 — Capturing commitments from meetings

### US-4.1 — Upload a transcript
**As a** CoS after a leadership meeting
**I want to** upload the transcript file or paste the text
**So that** Verato extracts the commitments without me re-typing

**Acceptance criteria**
- Form with: meeting title, date, optional participants, transcript body
- Drag-drop zone accepts .txt .docx .pdf .vtt .srt
- "or paste transcript" textarea fallback in monospace font
- Submit disabled until title + date + (file or text) all present
- Submit shows full-page "Extracting commitments…" spinner with explanatory copy
- Auto-routes to Extraction Review when complete

**API needs:** ✅ `POST /api/v1/meetings/` with multipart · 🆕 `meeting_type` selector · 🆕 auto-detect format (Zoom/Granola/Otter) · 🆕 `POST .../extract/` for re-trigger

---

### US-4.2 — Review what the LLM extracted
**As a** CoS
**I want to** see every extracted commitment with its confidence score, then confirm or reject
**So that** only verified items enter my tracker

**Acceptance criteria**
- Header: meeting title, counts ("12 found · 9 confirmed · 3 pending review")
- Confidence legend row at top with thresholds (≥0.80 high · 0.65–0.79 review · <0.65 low)
- Each item row shows: confidence score (mono, colour-coded), normalised text, owner, deadline, tags
- Per-row green ✓ (confirm) and red ✕ (reject) buttons
- Confirmed rows tint sage; rejected rows fade out
- "Undo" link for any decided item

**API needs:** ✅ `GET .../pending-commitments/` · ✅ `POST .../<id>/confirm/` · ✅ `POST .../<id>/reject/` · 🆕 `suggested_priority` + `suggested_tags` per pending item · 🆕 `learning_source` for explainability

---

### US-4.3 — Bulk-confirm high-confidence items
**As a** CoS reviewing a transcript with 15 items
**I want to** one-click confirm everything ≥ 0.80
**So that** I only spend time on the borderline cases

**Acceptance criteria**
- "Confirm all ≥ 0.80" button in header
- Affects only items currently in pending state (not previously rejected)
- All affected rows transition to confirmed state with the green tint
- Counts in header update immediately

**API needs:** 🆕 `POST /api/v1/pending-commitments/bulk-confirm/` accepting `{ids: [], min_confidence?: 0.80}`

---

### US-4.4 — Edit before confirming
**As a** CoS
**I want to** correct the LLM's mistakes (wrong owner, fuzzy deadline, missing tag) before confirming
**So that** I don't have to confirm-then-edit in two steps

**Acceptance criteria** *(prototype: not yet implemented — proposed UX)*
- Each pending row's text/owner/deadline/priority/tags are editable inline
- Edits persist as part of the confirm action
- Visual indicator on rows that have been edited from the LLM's original suggestion

**API needs:** ⚠️ `PATCH /api/v1/pending-commitments/<id>/` (edit before confirm)

---

### US-4.5 — Push confirmed items into the tracker
**As a** CoS done reviewing
**I want to** push all confirmed items to the active tracker in one click
**So that** the Dashboard shows them and Slack scheduling can begin

**Acceptance criteria**
- Primary CTA in header: "Add N to tracker →"
- Disabled until at least one item is confirmed AND none are still pending
- After click: success state, then auto-routes to Dashboard
- Dashboard reflects the new commitments immediately

**API needs:** ✅ confirmation endpoints already create commitment records · 🆕 `POST .../meetings/<id>/finalise/` could be a single batch endpoint

---

## Epic 5 — Slack nudges (owner side)

### US-5.1 — Receive a clear, actionable nudge
**As an** Owner
**I want to** receive a Slack DM that tells me exactly what's expected and lets me respond in one click
**So that** I don't need to switch contexts to log my status

**Acceptance criteria** *(prototype: Slack message preview screen — proposed)*
- DM from Verato bot includes: the commitment text, the deadline (relative + absolute), source meeting
- 3 reply buttons: ✅ Done · ⏱ Need more time · 🚫 Blocked
- "Need more time" opens a date picker
- "Blocked" opens a free-text input
- "View in Verato" link opens the commitment detail page

**API needs:** ✅ Slack bot infra · ✅ button webhook handling · 🆕 deep link from Slack to web detail screen with auth

---

### US-5.2 — Get nudged at the right time
**As an** Owner
**I want** nudges to arrive at sensible times in my time zone
**So that** I'm not woken up by Verato

**Acceptance criteria** *(proposed)*
- Default quiet hours: 8pm–8am owner local time
- Org-level override possible (e.g. trading floor wants 7am)
- Per-person quiet hours editable in their profile
- Nudges queued during quiet hours, sent at next valid window

**API needs:** 🆕 `quiet_hours` field on Person · 🆕 `PATCH /api/v1/people/<id>/preferences/` · 🆕 scheduler aware of quiet windows

---

## Epic 6 — Team & settings

### US-6.1 — Invite colleagues
**As an** Admin (CoS) on a Team plan
**I want to** invite colleagues by email
**So that** they can log in and see the tracker too

**Acceptance criteria**
- Settings → Team tab → "Invite colleague" button
- Inline form with single email input
- "Send invite" sends and shows "Sent ✓" success state
- Invitee appears in members list as PENDING until they accept
- 7-day invite link mentioned in helper copy

**API needs:** ✅ `POST /api/v1/orgs/<id>/invitations/` · 🆕 resend / revoke endpoints

---

### US-6.2 — Manage Slack integration post-onboarding
**As an** Admin
**I want to** see whether Slack is connected, test it, and reconnect if needed
**So that** I can trust nudges are actually getting through

**Acceptance criteria**
- Settings → Slack tab
- If connected: green status card with workspace name + "● Connected" pill
- If not: "Add to Slack" CTA (matches onboarding screen)
- Section to enter / verify the Admin's own Slack user ID with helper copy ("Find it in Slack: click your name → Copy member ID")

**API needs:** 🆕 `GET .../slack/status/` · 🆕 `POST .../slack/test-message/` · 🆕 `PATCH /api/v1/users/<id>/` with `slack_user_id`

---

### US-6.3 — Tune extraction confidence threshold
**As an** Admin
**I want to** set the org-wide threshold below which the LLM's extractions need manual review
**So that** I can balance "review fatigue" against "missed commitments"

**Acceptance criteria**
- Settings → Organisation tab
- Slider 0.50 to 0.95, step 0.05, default 0.65
- Live numeric readout in monospace
- Helper copy: "Commitments below this confidence are shown for manual review"
- Save button persists

**API needs:** ⚠️ `PATCH /api/v1/orgs/<id>/` with `extraction_confidence_threshold`

---

## Epic 7 — People & analytics

### US-7.1 — See per-person delivery performance
**As a** CoS
**I want** a People page that shows everyone's commitment count and delivery rate
**So that** I know who's reliable and who needs a check-in

**Acceptance criteria**
- People page shows one card per tracked participant
- Each card: avatar, name, role, total commitments, meeting count, delivery rate (bar + percentage)
- Delivery rate colour-coded (≥85% sage, 65–84% amber, <65% rose)
- Cards are clickable (future: drill-in to person profile)

**API needs:** ✅ `GET /api/v1/people/` with aggregate fields · ⚠️ `delivery_rate` computed field

---

### US-7.2 — Browse meeting history
**As a** CoS
**I want** a Meetings page that lists every transcript I've uploaded with extraction status
**So that** I can find that meeting from 3 weeks ago and re-review

**Acceptance criteria**
- Meetings list shows columns: title, type, date, commitment count
- Done indicator per row
- Click → re-opens the Extraction Review for that meeting
- Same Upload + Import CTAs as Dashboard in header

**API needs:** ✅ `GET /api/v1/meetings/` · 🆕 click-to-re-review behaviour relies on extraction status field

---

## Cross-cutting expectations

These are not screen-specific but show up across the prototype:

### US-X.1 — Trustworthy audit trail
**As a** CoS using Verato as my source of truth
**I want** every state change to be timestamped and attributed
**So that** I can defend the tracker in a leadership review

- Every commitment shows full event history
- Events include: extraction, confirmation, status changes, nudges sent, owner replies, manual edits
- Timestamps in UTC stored, local time displayed

### US-X.2 — Forgiving by default
**As a** CoS who misclicks
**I want** an Undo on every destructive action
**So that** I never lose data to a bad click

- Reject in extraction review → undo
- Cancel a commitment → recoverable from history
- Defer with wrong date → editable in the same UI

### US-X.3 — Respectful of my time
**As a** CoS
**I want** the UI to be dense, fast, and keyboard-driven
**So that** Verato saves time, not consumes it

- Dashboard renders ≤200ms
- All primary actions are 1 click from dashboard
- Status filters are tabs, not dropdowns
- Keyboard nav (planned): J/K through rows, Enter to open, ⌘K command palette

---

## Out of scope for v0.3 (deferred user stories)

These have been considered and intentionally postponed:

| Story | Reason |
|---|---|
| Saved views ("My Monday morning") | Phase 2 — needs user research on common combos first |
| Bulk multi-select on dashboard | Phase 2 — adds UI complexity; design partners haven't asked |
| Real-time WebSocket updates | Phase 2 — manual refresh is acceptable for MVP |
| Dependency / blocker links between commitments | Phase 2 — most users keep this in their head |
| Person profile drill-in | Phase 2 — current People cards are sufficient signal |
| Weekly digest email designer | Phase 2 — backend job is enough; no UI needed yet |
| Slack nudge template editor | Phase 2 — defaults work for design partners |
| Custom tag taxonomy / approved-list mode | Phase 3 — only needed for orgs with strict governance |
| SSO (Google Workspace) | Phase 3 — design partners are 1–5 person teams |
| Audit log export | Phase 3 — compliance feature, not MVP |
| Per-team sub-orgs | Phase 3 — needs full team data model |

---

## Phase 2: LLM context learning

See `DESIGN_README.md` for the implementation sketch. In user-story shorthand:

> **As a** CoS who has overridden the LLM's priority suggestion 4 times for "board deck" tagged items
> **I want** the LLM to start suggesting HIGH priority for new "board deck" items automatically
> **So that** I'm not doing the same correction every week

This is the seed that grows into per-org prompt augmentation, weekly re-rank batch jobs, and the `extraction_feedback` table. Out of scope for design partner phase.
