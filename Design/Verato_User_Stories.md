Verato — User Stories
Product specification anchored in the v0.3 prototype
Status legend: ✅ supported by current spec  ·  ⚠️ partial  ·  🆕 new endpoint/field needed

# Personas

# Epic 1 — Sign-up & onboarding
## US-1.1 — Pick a plan
As a: New user
I want to: See the available plans before I create an account
So that: I know whether I'm signing up alone or for my team
Acceptance criteria
- Plan picker shows two cards: Individual and Team
- "Team" is visually marked as RECOMMENDED
- Each card lists 4 differentiating features (logins, Slack workspaces, invites, extraction)
- Both plans show "no credit card · free for 3 months" copy
- Clicking either card carries the plan choice into the sign-up form
API needs: 🆕 GET /api/v1/billing/plans/ (live plan defs) · ✅ no backend call needed for MVP if plans are hard-coded

## US-1.2 — Create my account
As a: New user
I want to: Create my account in a single short form
So that: I can start using Verato in under a minute
Acceptance criteria
- Form captures: name, work email, password, organisation name
- Inline validation: email format, password ≥ 8 chars
- Back button returns to plan picker (preserving plan)
- Submit shows "Creating account…" loading state then auto-advances to onboarding
- Error states are inline per-field, not in a banner
API needs: ✅ POST /api/v1/auth/register/ · ✅ org_name + plan in payload · ✅ is_first_login flag in response · ✅ GET /api/v1/auth/me/ (Week 9 — session check + org context on every page load) · 🆕 email verification endpoints

## US-1.3 — Connect Slack during onboarding
As a: CoS
I want to: Connect my Slack workspace as part of onboarding
So that: Verato can send nudges to commitment owners on my behalf
Acceptance criteria
- Step indicator shows position 1/4 in the onboarding journey
- Page explains why Slack is needed (one sentence)
- Lists the 3 scopes Verato will request (DMs, button responses, no channel access)
- "Add to Slack" CTA in Slack-purple branding
- "Skip for now — connect later from Settings" option
- Skip and connect both route forward to the Import step
API needs: ✅ GET /api/v1/slack/oauth/start/?auth=<JWT> (Week 9 — JWT param ensures correct user when browser session cookie is stale) · ✅ OAuth callback · ✅ GET /api/v1/slack/status/ · ✅ POST /api/v1/slack/test-message/

## US-1.4 — Import my existing tracker
As a: CoS
I want to: Drag in my existing spreadsheet or paste my notes from another tool
So that: Verato is useful from minute one, not week three
Acceptance criteria
- Drag-drop zone accepts .csv .xlsx .docx .txt .md
- Visual feedback while dragging (border + tint)
- Filename is shown after drop with a clear × to remove
- "or paste text" divider with textarea fallback
- Disabled "Extract items" button until file or text present
- "I'll start fresh" skip option
- After extraction completes, routes to Extraction Review with source = 'import'
API needs: ✅ POST /api/v1/meetings/import/ · ✅ GET /api/v1/meetings/{id}/status/ for progress polling · ✅ imported commitments have source=import

# Epic 2 — Daily command centre (Dashboard)
## US-2.1 — See what needs my attention right now
As a: CoS opening Verato in the morning
I want to: See at a glance how many things are overdue, at risk, on track
So that: I can prioritise my day in the first 10 seconds
Acceptance criteria
- 4 stat cards at the top: Overdue · At Risk · On Track · Total Active
- Counts are colour-coded (rose / amber / sage / neutral)
- Clicking a stat filters the list below to that status
- Numbers use monospace type for stable alignment
- "Week of [date]" subtitle anchors the view in time
API needs: ✅ GET /api/v1/dashboard/ (single aggregate) · ✅ filtered list endpoints

## US-2.2 — Filter commitments by status
As a: CoS
I want to: Switch between status views with one click
So that: I can focus on overdue items, then sweep at-risk, then check delivered
Acceptance criteria
- Tab row: All active · Needs attention · At risk · On track · Done
- Active tab is underlined in accent colour with bold text
- List below updates instantly without page reload
- "Nothing here — all clear" empty state with a check icon
API needs: ✅ GET /api/v1/commitments/?status=<>

## US-2.3 — Filter by priority
As a: CoS
I want to: Filter the dashboard to only P1 (or P1+P2) commitments
So that: I can ignore noise during a busy week
Acceptance criteria
- Priority chips (P1, P2, P3) in the filter row, right-aligned
- Multi-select — clicking chips toggles them on/off
- Active chips have a filled background; inactive are outlined
- Filters compose with status tabs (e.g. "At risk + P1")
- "Clear" link appears when any chip is active
API needs: ✅ GET /api/v1/commitments/?priority=high · ✅ priority field on Commitment model

## US-2.4 — Filter by tag with one click
As a: CoS preparing for a board meeting
I want to: Click any tag and see every commitment with that tag
So that: I can pull together "everything tagged board prep" without typing a query
Acceptance criteria
- Every tag pill in every dashboard row is clickable
- Click → page filters to that tag instantly
- A banner appears below the filter row: "Filtered by tag: #pricing · clear ×"
- Banner persists across status / priority filter changes
- Clear × removes only the tag filter, not other filters
API needs: ✅ GET /api/v1/commitments/?tags__label=<> · ✅ GET /api/v1/tags/ for tag library + autocomplete

## US-2.5 — Scan commitments efficiently
As a: CoS
I want: Each row to show the most important context without me clicking
So that: I can triage 30 items in 60 seconds
Acceptance criteria
- Each row shows: priority bar, risk dot (red/amber/green), title, source meeting, owner avatar+name, deadline, status badge
- Rows hover to a subtle background lift
- "Nudge sent N times" inline meta when applicable
- Overdue items auto-promote their status badge to OVERDUE regardless of stored status
- Sort: overdue first, then descending by risk score
API needs: ✅ commitment list with embedded owner, meeting, escalation count

## US-2.6 — Get to the right action fast
As a: CoS
I want: Upload and Import buttons in the dashboard header
So that: I don't have to navigate away to add new content
Acceptance criteria
- Top-right of dashboard: secondary 'Import' button + primary 'Upload transcript' button
- Both icons + labels
- Upload routes to the Upload Transcript form
- Import routes to the same flow as onboarding-import (with no skip option)
API needs: N/A (navigation only)

# Epic 3 — Working a single commitment
## US-3.1 — See the full context of one commitment
As a: CoS
I want to: Click a commitment and see every detail in one screen
So that: I have full context before nudging the owner or deferring
Acceptance criteria
- Page header: title, status badge (large), back link to dashboard
- 4-cell meta grid: Owner (with avatar + role) · Deadline · Source (meeting + date) · Confidence (bar + score)
- Risk score component: percentage, coloured progress bar, formula breakdown (50% deadline / 35% owner / 15% recency)
- Original quote in an italic accent-bordered block
- Tags as pills below
API needs: ✅ GET /api/v1/commitments/{id}/ · ⚠️ risk_score_breakdown field needed

## US-3.2 — Take action on a commitment
As a: CoS
I want to: Resolve, defer, escalate, or nudge from the detail screen
So that: I don't need to go elsewhere to act
Acceptance criteria
- 4 action buttons: Send nudge · Mark done · Defer · Cancel
- Send nudge disabled if nudge sent in last 20 hours (shows 'Sent Xhr ago')
- Defer opens a date picker inline
- Cancel prompts 'Are you sure?' with undo option
- All actions create an event in the history timeline
API needs: ✅ POST /api/v1/commitments/{id}/escalate/ · resolve/ · reopen/ · ✅ Slack nudge endpoint

## US-3.3 — Read the full audit history
As a: CoS
I want to: See a timestamped log of everything that has happened to a commitment
So that: I can defend the tracker in a leadership review
Acceptance criteria
- Timeline below the actions panel
- Events: extraction, confirmation, status changes, nudges sent, owner replies, manual edits
- Timestamps shown in local time, UTC stored
- Owner replies shown verbatim (Done / Delayed / Blocked)
API needs: ✅ EscalationEvent + ExtractionFeedback + CommitmentEvent tables · ✅ GET /api/v1/commitments/{id}/history/ unified audit log

# Epic 4 — Extraction review
## US-4.1 — Review AI-extracted commitments
As a: CoS
I want to: See the AI's extracted commitments and confirm or reject them
So that: Only real commitments enter my tracker
Acceptance criteria
- List shows: commitment text, confidence score, proposed owner, proposed deadline
- Confidence shown as a coloured bar and percentage
- Each row has Confirm and Reject buttons
- Confirmed items move to the tracker; rejected items are logged as feedback
API needs: ✅ GET /api/v1/commitments/?status=pending_review · POST .../confirm/ · .../reject/

## US-4.2 — Batch-confirm high-confidence items
As a: CoS
I want to: Confirm all items above 0.80 confidence in one click
So that: I don't have to click through 20 items one by one
Acceptance criteria
- "Confirm all above 0.80 →" button in the header
- Only items meeting the threshold are confirmed; others remain for individual review
- Threshold is the org's configured confidence_threshold
- Button shows count: 'Confirm 7 high-confidence items →'
API needs: ✅ POST /api/v1/commitments/bulk-confirm/ {min_confidence: 0.80, meeting: <id>}

## US-4.3 — Correct the owner attribution
As a: CoS
I want to: Change the owner before confirming
So that: The nudge goes to the right person
Acceptance criteria
- Owner field is editable inline (typeahead from existing persons)
- Selecting a new owner logs a WRONG_OWNER feedback signal
- The commit still confirms with the corrected owner
API needs: ✅ PATCH /api/v1/commitments/{id}/ · ✅ ExtractionFeedback with type=WRONG_OWNER

## US-4.4 — Correct the deadline
As a: CoS
I want to: Fix a misread deadline before confirming
So that: The nudge timing is correct
Acceptance criteria
- Deadline field is editable inline (date picker)
- Editing logs a WRONG_DATE feedback signal
- Edits persist as part of the confirm action
- Visual indicator on rows that have been edited from the LLM's original suggestion
API needs: ✅ PATCH /api/v1/commitments/{id}/ (edit before confirm — normalised_text, owner, deadline all writable)

## US-4.5 — Push confirmed items into the tracker
As a: CoS done reviewing
I want to: Push all confirmed items to the active tracker in one click
So that: The Dashboard shows them and Slack scheduling can begin
Acceptance criteria
- Primary CTA in header: 'Add N to tracker →'
- Disabled until at least one item is confirmed AND none are still pending
- After click: success state, then auto-routes to Dashboard
- Dashboard reflects the new commitments immediately
API needs: ✅ confirmation endpoints already create commitment records · ✅ POST /api/v1/commitments/bulk-confirm/ as batch endpoint

# Epic 5 — Slack nudges (owner side)
## US-5.1 — Receive a clear, actionable nudge
As an: Owner
I want to: Receive a Slack DM that tells me exactly what's expected and lets me respond in one click
So that: I don't need to switch contexts to log my status
Acceptance criteria
- DM from Verato bot includes: the commitment text, the deadline (relative + absolute), source meeting
- 3 reply buttons: Done · Need more time · Blocked
- "Need more time" opens a date picker
- "Blocked" opens a free-text input
- "View in Verato" link opens the commitment detail page
API needs: ✅ Slack bot infra · ✅ button webhook handling · ⚠️ deep link from Slack to web detail screen with auth

## US-5.2 — Get nudged at the right time
As an: Owner
I want: Nudges to arrive at sensible times in my time zone
So that: I'm not woken up by Verato
Acceptance criteria
- Default quiet hours: 8pm–8am owner local time
- Org-level override possible (e.g. trading floor wants 7am)
- Per-person quiet hours editable in their profile
- Nudges queued during quiet hours, sent at next valid window
API needs: 🆕 quiet_hours field on Person · 🆕 PATCH /api/v1/people/<id>/preferences/ · 🆕 scheduler aware of quiet windows

# Epic 6 — Team & settings
## US-6.1 — Invite colleagues
As an: Admin (CoS) on a Team plan
I want to: Invite colleagues by email
So that: They can log in and see the tracker too
Acceptance criteria
- Settings → Team tab → 'Invite colleague' button
- Inline form with single email input
- "Send invite" sends and shows "Sent ✓" success state
- Invitee appears in members list as PENDING until they accept
- 7-day invite link mentioned in helper copy
API needs: ✅ POST /api/v1/auth/invite/ · ✅ GET /api/v1/auth/invitations/ (list sent invites) · 🆕 resend / revoke endpoints

## US-6.2 — Manage Slack integration post-onboarding
As an: Admin
I want to: See whether Slack is connected, test it, and reconnect if needed
So that: I can trust nudges are actually getting through
Acceptance criteria
- Settings → Slack tab
- If connected: green status card with workspace name + "● Connected" pill
- If not connected: "Add to Slack" CTA (matches onboarding screen)
- Section to enter / verify the Admin's own Slack user ID with helper copy
API needs: ✅ GET /api/v1/slack/status/ · ✅ POST /api/v1/slack/test-message/ · ✅ POST /api/v1/persons/{id}/link-slack/ to set slack_user_id

## US-6.3 — Tune extraction confidence threshold
As an: Admin
I want to: Set the org-wide threshold below which the LLM's extractions need manual review
So that: I can balance "review fatigue" against "missed commitments"
Acceptance criteria
- Settings → Organisation tab
- Slider 0.50 to 0.95, step 0.05, default 0.65
- Live numeric readout in monospace
- "Commitments below this confidence are shown for manual review" helper copy
- Save button persists
API needs: ✅ PATCH /api/v1/orgs/{id}/settings/ with confidence_threshold

# Epic 7 — People & analytics
## US-7.1 — See per-person delivery performance
As a: CoS
I want: A People page that shows everyone's commitment count and delivery rate
So that: I know who's reliable and who needs a check-in
Acceptance criteria
- People page shows one card per tracked participant
- Each card: avatar, name, role, total commitments, meeting count, delivery rate (bar + percentage)
- Delivery rate colour-coded (≥85% sage, 65–84% amber, <65% rose)
- Cards are clickable (future: drill-in to person profile)
API needs: ✅ GET /api/v1/persons/ with aggregate fields · ✅ delivery_rate computed field · ✅ POST (create) · ✅ PATCH (edit) · ✅ POST /persons/merge/ (deduplicate)

## US-7.2 — Browse meeting history
As a: CoS
I want: A Meetings page that lists every transcript I've uploaded with extraction status
So that: I can find that meeting from 3 weeks ago and re-review
Acceptance criteria
- Meetings list shows columns: title, type, date, commitment count
- Done indicator per row
- Click → re-opens the Extraction Review for that meeting
- Same Upload + Import CTAs as Dashboard in header
API needs: ✅ GET /api/v1/meetings/ · ✅ processing_status field enables re-review routing · ✅ PATCH /meetings/{id}/ to edit title/date/type/summary · ✅ GET /meetings/{id}/participants/ · ✅ POST /meetings/{id}/link-participants/

# Cross-cutting expectations
## US-X.1 — Trustworthy audit trail
As a: CoS using Verato as my source of truth
I want: Every state change to be timestamped and attributed
So that: I can defend the tracker in a leadership review
- Every commitment shows full event history via GET /commitments/{id}/history/
- Events include: extraction, confirmation, status changes, nudges sent, owner replies, manual field edits
- CommitmentEvent model stores old_value/new_value JSON for field edits; EscalationEvent records escalation chain
- Timestamps in UTC stored, local time displayed
API needs: ✅ CommitmentEvent model · ✅ GET /api/v1/commitments/{id}/history/ (unified log)

## US-X.2 — Forgiving by default
As a: CoS who misclicks
I want: An Undo on every destructive action
So that: I never lose data to a bad click
- Reject in extraction review → undo
- Cancel a commitment → recoverable from history
- Defer with wrong date → editable in the same UI

## US-X.3 — Respectful of my time
As a: CoS
I want: The UI to be dense, fast, and keyboard-driven
So that: Verato saves time, not consumes it
- Dashboard renders ≤200ms
- All primary actions are 1 click from dashboard
- Status filters are tabs, not dropdowns
- Keyboard nav (planned): J/K through rows, Enter to open, ⌘K command palette

# Out of scope for v0.3 (deferred user stories)
These have been considered and intentionally postponed:


# Phase 2 — LLM context learning
As a CoS who has overridden the LLM's priority suggestion 4 times for 'board deck' tagged items, I want the LLM to start suggesting HIGH priority for new 'board deck' items automatically, so that I'm not doing the same correction every week.
This is the seed that grows into per-org prompt augmentation, weekly re-rank batch jobs, and the extraction_feedback table. Out of scope for design partner phase.