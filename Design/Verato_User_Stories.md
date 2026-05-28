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
API needs: ✅ POST /api/v1/auth/invite/ · ✅ GET /api/v1/auth/invitations/ (list sent invites) · ✅ POST /api/v1/auth/invitations/{id}/resend/ · ✅ DELETE /api/v1/auth/invitations/{id}/revoke/

## US-6.1b — Delegate meeting management to a colleague ✅
As a: CoS
I want to: Give a colleague access to manage my meetings and commitments
So that: They can act on my behalf when I'm unavailable
Acceptance criteria
- Settings → Team tab → Delegation section
- Search platform users in my org, pick one, send delegation request
- Pending delegations shown with status — colleague must accept before getting access
- Accepted delegates appear in a separate list with revoke option
- Delegate sees a pending request in their own Settings → Team tab and can accept/decline
- Once accepted: delegate has full CoS access to my meetings (can confirm, resolve, escalate, nudge)
- Either party can remove the delegation at any time
API needs: ✅ GET /api/v1/managers/ · ✅ POST /api/v1/managers/ {manager_user_id} · ✅ POST /api/v1/managers/{id}/accept/ · ✅ DELETE /api/v1/managers/{id}/ · ✅ GET /api/v1/persons/?is_platform_user=true (user_id field for manager_user_id)

## US-6.1c — Log an update as an action owner ✅
As an: Action owner (commitment assignee)
I want to: Log a status update on a commitment assigned to me
So that: My CoS knows I'm working on it without needing a Slack nudge
Acceptance criteria
- Commitment detail page shows "Log Update" button regardless of role
- Free-text field to describe current status
- On submit: CoS receives an in-app notification immediately
- Update appears in the commitment history timeline
- Action owner CANNOT mark as done/deferred/cancelled — only CoS can close commitments
API needs: ✅ POST /api/v1/commitments/{id}/log-update/ {response: "..."} · ✅ InAppNotification(type=owner_update) created for CoS · ✅ can_manage field on CommitmentSerializer gates CoS-only actions

## US-6.2 — Manage Slack integration post-onboarding
As an: Admin
I want to: See whether Slack is connected, test it, and reconnect if needed
So that: I can trust nudges are actually getting through
Acceptance criteria
- Settings → Slack tab
- If connected: green status card with workspace name + "● Connected" pill + Disconnect button
- If not connected: "Add to Slack" CTA (matches onboarding screen)
- Section to enter / verify the Admin's own Slack user ID with helper copy
API needs: ✅ GET /api/v1/slack/status/ · ✅ POST /api/v1/slack/test-message/ · ✅ POST /api/v1/persons/{id}/link-slack/ · ✅ POST /api/v1/slack/disconnect/

## US-6.4 — Manage Gmail integration
As an: Admin
I want to: Connect my Gmail account so Verato can send nudge emails and read replies
So that: I have a full email nudge loop without leaving Verato
Acceptance criteria
- Settings → Gmail tab
- If connected: green status, email address shown, Disconnect button
- If not connected: "Connect Gmail" CTA starts OAuth flow
- Polling frequency configurable (15 / 30 / 60 / 120 min) with enable/disable toggle
- Note: Gmail API must be enabled in Google Cloud Console for the OAuth project
API needs: ✅ GET /api/v1/gmail/status/ · ✅ GET /api/v1/gmail/oauth/start/ · ✅ POST /api/v1/gmail/disconnect/ · ✅ PATCH /api/v1/nudge-settings/ (polling frequency)

## US-6.5 — Connect Google Calendar for automatic Meet transcript pickup
As an: Admin
I want to: Connect my Google Calendar so Verato automatically processes Google Meet transcripts
So that: I never have to manually upload a transcript from a Google Meet call
Acceptance criteria
- Settings → Integrations → Google Calendar card
- If connected: green status, connected email shown, "Transcripts detected" badge (or "Not detected" if Google Meet transcription is not enabled in Workspace admin), Disconnect button
- If not connected: "Connect Google Calendar" CTA opens OAuth popup
- On connect: Verato requests `calendar.readonly` + `drive.readonly` scopes
- After connecting, meetings with Google Meet links appear automatically in the Meetings list once their transcript is available (~2–5 min after call ends)
- If transcripts are never found: user is shown a message explaining that Google Meet transcription must be enabled in Google Workspace admin
API needs: ✅ GET /api/v1/calendar/status/ · ✅ GET /api/v1/calendar/oauth/start/?auth=<jwt> · ✅ POST /api/v1/calendar/disconnect/

## US-6.6 — Connect Zoom for automatic recording transcript pickup
As an: Admin
I want to: Connect my Zoom account so Verato automatically processes Zoom cloud recording transcripts
So that: I never have to manually upload a transcript from a Zoom call
Acceptance criteria
- Settings → Integrations → Zoom card
- If connected: green status, connected Zoom email shown, Disconnect button
- If not connected: "Connect Zoom" CTA opens OAuth popup
- After connecting: whenever a Zoom cloud recording completes, Verato receives a webhook and processes the VTT transcript automatically (typically within 2 min of recording finishing)
- Requirements note: Zoom Pro/Business with Cloud Recording enabled; recording must include transcript
API needs: ✅ GET /api/v1/zoom/status/ · ✅ GET /api/v1/zoom/oauth/start/?auth=<jwt> · ✅ POST /api/v1/zoom/disconnect/ (webhook handled server-side)

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

# Epic 8 — In-app notifications

## US-8.1 — See owner responses without checking email or Slack
As a: CoS
I want to: See a notification badge in the app whenever an owner responds to a nudge
So that: I always know when something has changed without switching context
Acceptance criteria
- Bell icon in the top nav shows a red badge with unread count
- Clicking the bell opens a notification feed
- Each notification shows: who responded, what commitment, what they did (Done / Delayed / Blocked / email reply)
- Clicking a notification goes directly to the commitment detail
- Marking one or all as read clears the badge
- Notifications are created instantly on Slack button clicks; within the polling window for Gmail replies (30 min default)
API needs: ✅ GET /api/v1/notifications/ · ✅ GET /api/v1/notifications/unread-count/ · ✅ POST /api/v1/notifications/<id>/read/ · ✅ POST /api/v1/notifications/mark-all-read/

## US-8.2 — Understand what the owner actually said
As a: CoS
I want: The notification to tell me the intent of the reply, not just that a reply came in
So that: I can act on it without opening the email or Slack thread
Acceptance criteria
- Notification message is human-readable: "Sarah marked 'Send slides to board' as Done via Slack"
- For Gmail replies: intent is Gemini-parsed (done / deferred / blocked / replied) and surfaced in the message
- If Gemini couldn't parse the intent, notification still fires with "replied via email"
API needs: ✅ Gemini parse in poll_gmail_replies task · ✅ create_cos_notification called after parse

# Epic 9 — Auth, Legal & Security

## US-9.1 — Accept terms before creating an account
As a: New user
I want to: See and accept the Terms of Service and Privacy Policy before I create an account
So that: I know what I'm agreeing to and the product has legal cover
Acceptance criteria
- Register screen has a required checkbox: "I agree to the Terms of Service and Privacy Policy" with hyperlinked terms
- Checkbox must be checked to enable the Create Account button
- Backend enforcement deferred — `terms_accepted_at` field not added to User model
- Frontend handles consent UX; static `/terms` and `/privacy` pages exist
- Static `/terms` and `/privacy` pages exist in the frontend
API needs: ✅ `/terms` and `/privacy` static pages (frontend) · ⏸ `terms_accepted` payload + `User.terms_accepted_at` deferred (frontend enforces consent)

## US-9.2 — Verify my email on registration ✅
As a: New user registering
I want to: Verify my email address with a 6-digit code before I can log in
So that: Only real email addresses can create accounts
Acceptance criteria
- OTP is sent on **first registration only** — login is direct email+password thereafter
- Registration creates `User(is_active=False)` + sends 6-digit OTP via Amazon SES
- Registration returns `{verification_required: true, session_token}` (not JWT)
- OTP entry screen: 6-digit code, expires in 10 minutes, max 5 wrong attempts
- Correct OTP → `user.is_active=True` + JWT issued, user lands on Dashboard
- "Activate your account" resend flow for stuck unverified users via `POST /auth/resend-verification/`
- Inactive user login auto-redirects to OTP flow with a fresh code (password is still verified first)
- Invited users accepted via invite link are created `is_active=True` — no OTP needed
API needs: ✅ `POST /auth/register/` returns `{verification_required, session_token}` · ✅ `POST /auth/verify-email/ {session_token, code}` → JWT · ✅ `POST /auth/resend-verification/ {email, password}` · ✅ `POST /auth/token/` auto-redirects inactive users

## US-9.3 — Reset my password when I've forgotten it ✅
As a: User who has forgotten their password
I want to: Reset my password using a code sent to my email
So that: I can regain access without contacting support
Acceptance criteria
- "Forgot password?" link on Login screen
- Email input screen: enter registered email, click "Send reset code"
- Response is always the same message regardless of whether email exists (prevents enumeration)
- OTP entry screen — same 6-box design as registration OTP
- After correct OTP: new password screen (min 8 chars, confirm field)
- On success: all existing refresh tokens blacklisted, redirect to Login with "Password updated" message
- OTP expires in 10 minutes and is single-use (max 5 attempts)
API needs: ✅ `POST /auth/password/reset/ {email}` (silent 200 — no enumeration) · ✅ `POST /auth/password/reset/confirm/ {email, otp, new_password}` (blacklists all refresh tokens on success)

## US-9.4 — Read the Privacy Policy and Terms at any time
As a: User
I want to: Access the Privacy Policy and Terms of Service from the login page and settings
So that: I can review what data is collected and how it's used at any time
Acceptance criteria
- Footer links on Login and Register screens
- Link in Settings → Organisation tab
- Pages are readable on mobile, no login required
API needs: Static pages only — no backend required

# Epic 10 — Strategic Initiatives

## US-10.1 — Promote a tag to a Strategic Initiative ✅
As a: CoS who manages multiple concurrent workstreams
I want to: Promote any commitment tag to a named Strategic Initiative with a description
So that: I can see the health of a whole theme at a glance without opening individual commitments
Acceptance criteria
- Any tag can be toggled to is_initiative=true with a description field
- Toggle appears inline in the Tag Management panel on the Initiatives screen (admin only)
- Promoted tags appear in the Initiatives view; plain tags do not
- Description is optional at promotion time — editable later
API needs: ✅ PATCH /api/v1/tags/{id}/ {is_initiative: true, description: "..."}

## US-10.2 — See initiative health at a glance ✅
As a: CoS preparing for an executive meeting
I want to: See each strategic initiative as a card with commitment counts and an AI summary
So that: I can brief a senior stakeholder in 30 seconds without pulling a spreadsheet
Acceptance criteria
- Initiatives screen shows one card per initiative
- Each card: initiative label, description, status pill row (Active / At Risk / Escalated / Done counts), AI summary text with timestamp
- Empty state if no initiatives exist yet
- "Refresh summary" button on each card regenerates the AI health summary
- Summary skips regeneration if summary is < 12h old and no commitments changed — returns cached with a note
- ?force=true on the API bypasses the staleness check
API needs: ✅ GET /api/v1/initiatives/ · ✅ POST /api/v1/tags/{id}/generate-summary/

## US-10.3 — Auto-tag a commitment with Gemini ✅
As a: CoS reviewing a freshly extracted commitment
I want to: Click one button and have Gemini suggest tags from my existing tag library
So that: Commitments are tagged consistently without me having to think about it every time
Acceptance criteria
- "Auto-tag" button on commitment detail / edit panel
- On click: spinner, then tags applied and displayed
- Toast shows which tags were applied: "Tags applied: product, q2 roadmap"
- Tags are added to existing tags, not replacing them
- Uses existing org tag library; only creates new tags for themes not already covered
API needs: ✅ POST /api/v1/commitments/{id}/auto-tag/

## US-10.4 — Manage tags: rename, merge, delete ✅
As an: Org admin cleaning up the tag library
I want to: Rename a tag, merge two duplicates into one, or delete an unused tag
So that: The tag library stays clean and useful as the org grows
Acceptance criteria
- Tag management panel (admin only) shows all tags with usage counts
- Rename: inline edit on any tag label
- Merge: pick a source tag and a target label — all commitments re-tagged, source deleted
- Delete: removes the tag from all commitments
- Non-admins can see tags but cannot manage them
API needs: ✅ PATCH /api/v1/tags/{id}/ · ✅ POST /api/v1/tags/{id}/merge/ {into: "label"} · ✅ DELETE /api/v1/tags/{id}/

# Out of scope for v0.3 (deferred user stories)
These have been considered and intentionally postponed:


# Phase 2 — LLM context learning
As a CoS who has overridden the LLM's priority suggestion 4 times for 'board deck' tagged items, I want the LLM to start suggesting HIGH priority for new 'board deck' items automatically, so that I'm not doing the same correction every week.
This is the seed that grows into per-org prompt augmentation, weekly re-rank batch jobs, and the extraction_feedback table. Out of scope for design partner phase.