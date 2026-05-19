# Verato — Product Specification & Key Screens
## Version 0.3 — MVP Complete / Phase 2 Planning

> **ICP:** Chief of Staff, Programme Manager at scale-ups (50–300 people)
> **Stack:** Django REST (AWS) · Next.js (GCP) · Gemini 2.5 Flash Lite · PostgreSQL 18
> **Design partner target:** 3 paying orgs by end of Month 3

---

## 1. Product Vision

Every week, commitments made in meetings get lost. Not because people are negligent — because no system owns them. They live in someone's notes, in a Notion page nobody revisits, in the memory of the person who ran the meeting. By the time anyone notices a commitment has slipped, the deadline has already passed.

Verato is the accountability layer that sits between meetings and outcomes. It reads every transcript, extracts every commitment, assigns it to an owner with a deadline, monitors its health, and nudges the right person at the right moment — automatically.

The primary user is the Chief of Staff. She is responsible for organisational accountability but has no reliable system for it today. Verato gives her one.

**The one-line pitch:** "Every commitment your organisation makes — tracked, owned, and surfaced before it slips."

---

## 2. The Problem

The Chief of Staff at a 100-person scale-up attends or covers 8–12 meetings a week. Across those meetings, 30–50 commitments are made. She has no system that reliably captures all of them, assigns ownership, tracks progress, or alerts her before something slips.

Her current workflow:
1. Manually scan meeting notes and recordings
2. Maintain a tracker in Notion or a spreadsheet — by hand
3. Chase owners via Slack DMs
4. Discover missed commitments at the next leadership meeting

This takes 3–5 hours every week. It is invisible, unscalable, and produces incomplete results.

The problem is not that she is disorganised. The problem is that **no tool was built for this job**.

### What exists today and why it fails

| Tool | Why it fails |
|---|---|
| Notion / Confluence | Manual. Only captures what someone types. No tracking, no nudges. |
| Jira / Linear | Task management, not commitment tracking. Requires everyone to be in the tool. |
| Meeting note AI (Otter, Fireflies) | Produces a summary. No structured extraction, no ownership, no status tracking. |
| CRM (Salesforce, HubSpot) | Tracks external commitments only. No internal accountability layer. |
| Email / Slack | Communication tools. No tracking, no history, no risk view. |

None of these tools own the commitment lifecycle. Verato does.

---

## 3. Who We're Building For

### Primary user — Chief of Staff

- At a scale-up (50–300 people) with an active exec team
- Attends or covers 8–12 meetings per week
- Responsible for ensuring commitments made by leadership are followed through
- Currently does this manually — spreadsheet, Notion, or memory
- Pain is highest on Monday mornings and the day before a leadership meeting
- Success metric: "I knew about every at-risk commitment before anyone had to ask me"

### Secondary user — Programme Manager

- Tracks commitments across multiple workstreams (not just one meeting type)
- Has similar pain to CoS but scoped to a programme or function
- Values delivery rate visibility by person and team

### Non-user (for MVP) — Commitment Owner

- Never logs into the product
- Receives a Slack DM 48 hours before their deadline
- Replies with a single button tap
- That reply updates the commitment status automatically
- If they do not reply, the CoS is notified

The product is designed to require zero behaviour change from individual contributors. They respond in Slack, which they already use.

---

## 4. Core Value Propositions

### 4.1 Extraction — turns meeting transcripts into structured commitments

AI reads the full transcript in a single call and extracts every explicit commitment: who promised what, by when. Each candidate is presented to the CoS for confirmation before it enters the tracker. High-confidence extractions can be batch-confirmed. Low-confidence ones are flagged for individual review.

### 4.2 Risk scoring — knows what is at risk before the CoS has to ask

Every active commitment has a live risk score computed from: deadline proximity (50%), owner's historical delivery rate (35%), and recency of updates (15%). The score is recomputed daily by a background task.

When a commitment crosses the AT_RISK threshold (score ≥ 0.70), it surfaces in the dashboard. When it crosses the ESCALATED threshold (score ≥ 0.90) or passes its deadline, the CoS is notified.

### 4.3 Slack nudges — automates the chasing

48 hours before a deadline, the owner receives a Slack DM with three response options: Done, Delayed, or Blocked. Their reply updates the commitment status immediately. If there is no reply within 24 hours, the CoS is notified.

The owner never needs to log in to Verato. Their entire interaction is a single Slack message.

### 4.4 Command centre — one view of everything at risk

The dashboard shows the CoS everything that needs attention, ordered by urgency. Overdue first, at-risk, then on track. One click opens the full detail with source quote and escalation options.

### 4.5 Self-serve onboarding — zero friction to get started

Any CoS can register their organisation, import their existing tracker, connect their Slack workspace, and invite colleagues — all without contacting sales. Individual users can sign up alone; teams add colleagues via email invite links.

---

## 5. Feature Set — Phased

### Phase 1 — The Core Loop (Complete)

| Feature | Status |
|---|---|
| Self-serve sign-up (individual + team plans) | ✓ Built |
| Team invite via email link (7-day token) | ✓ Built |
| Per-org Slack OAuth (each org connects own workspace) | ✓ Built |
| Manual transcript upload | ✓ Built |
| Prior commitments import | ✓ Built |
| Commitment extraction (explicit only) | ✓ Built |
| Extraction review (confirm / reject) | ✓ Built |
| Owner + deadline assignment | ✓ Built |
| Commitment tracker (dashboard) | ✓ Built |
| Commitment actions (confirm, reject, escalate, resolve) | ✓ Built |
| Risk scoring (daily Celery task) | ✓ Built |
| Slack nudge (Done / Delayed / Blocked) | ✓ Built |
| Weekly digest email (Gemini intro + SendGrid) | ✓ Built |
| Knowledge graph foundation (topics, tags, person timeline) | ✓ Built |

**What is explicitly not in Phase 1:**
- Cross-meeting conflict detection (requires embeddings)
- Implicit and conditional commitment extraction
- Dependency chain tracking
- Analytics dashboard
- Teams / Google Meet connectors
- Pre-meeting briefings
- Org-calibrated extraction recompilation

### Phase 2 — Intelligence Layer (Months 3–6)

| Feature | What it unlocks |
|---|---|
| Cross-meeting conflict detection | pgvector + Gemini Flash classification |
| Dependency chain tracking | Commitment B blocked on A → cascade risk |
| Implicit + conditional extraction | Expands coverage with calibration data |
| Accountability analytics | Delivery rate by person, team, time period |
| Pre-meeting briefing | Open commitments relevant to today's agenda |
| Org-calibrated extraction | Weekly recompile from ExtractionFeedback signals |
| Teams + Google Meet connectors | Full multi-platform auto-ingestion |

### Phase 3 — Platform Layer (Months 6–12)

| Feature | What it unlocks |
|---|---|
| Executive read-only dashboard | Leadership view without CoS access |
| Board / governance report export | PDF for board meetings |
| Jira / Linear integration | Push commitments as issues; sync status back |
| Multi-team / division view | Enterprise orgs with 5+ independent teams |
| SSO + SCIM provisioning | Enterprise security |
| Natural language query | "What have we committed to on EMEA pricing?" |
| Audit trail export | Legal and compliance |

---

## 6. User Roles

| Role | Access | How they get in |
|---|---|---|
| Org Admin | Full — all commitments, settings, invite-sending, Slack OAuth | Registers via `/auth/register/` |
| Chief of Staff | Full — all commitments, meetings, escalation controls | Invited via email link or is the Org Admin |
| Programme Manager | Full within their programme scope | Invited via email link |
| Commitment Owner | No login — Slack only | Receives nudge DM; presses button |
| Executive (Phase 2) | Read-only dashboard | Invited with restricted role |

---

## 7. Plans

### Individual plan
- 1 organisation
- 1 user with login (the CoS / Org Admin)
- 1 Slack workspace connection (optional)
- Unlimited persons (meeting participants who receive nudges via Slack but don't log in)

### Team plan
- 1 organisation
- Many users with logins (all connected via email invite)
- 1 Slack workspace connection (connected by the Org Admin)
- Each user links their own Slack user ID via the app
- Unlimited persons

Both plans are identical in functionality for MVP — the `plan` field is a label for billing purposes. No hard enforcement in the backend today.

---

## 8. The Core Loop

```
UPLOAD → EXTRACT → CONFIRM → MONITOR → NUDGE → RESOLVE
```

1. **Upload** — CoS uploads a transcript (paste, file, or Zoom auto-ingest)
2. **Extract** — Gemini reads the full transcript; returns commitment candidates with confidence scores
3. **Confirm** — CoS reviews candidates; confirms or rejects; high-confidence items can be batch-confirmed
4. **Monitor** — Risk scores recomputed daily; status transitions happen automatically
5. **Nudge** — Owner receives Slack DM 48hr before deadline; reply updates status
6. **Resolve** — Commitment closes as Delivered, Deferred, or Cancelled with full audit trail

---

## 9. Commitment Lifecycle

```
PENDING_REVIEW → ACTIVE → AT_RISK → ESCALATED
                       ↘              ↘
                     DEFERRED       DELIVERED
                                    CANCELLED
```

| Status | Meaning | How it gets there |
|---|---|---|
| PENDING_REVIEW | Extracted but not yet confirmed by CoS | Default after extraction |
| ACTIVE | Confirmed; being tracked; not yet at risk | CoS confirms |
| AT_RISK | Risk score ≥ 0.70 | Celery task daily |
| ESCALATED | Risk score ≥ 0.90, or past deadline, or CoS manually escalates | Celery task or CoS action |
| DELIVERED | Owner or CoS marks complete | Slack reply "Done" or CoS resolves |
| DEFERRED | New deadline set; clock resets | Slack reply "Delayed" or CoS edits |
| CANCELLED | Commitment withdrawn | CoS cancels |

---

## 10. Key Screens — MVP (Phase 1)

### Screen 1 — Sign-Up

**Route:** `/register`
**User:** New CoS or Org Admin — first person to create an account for their organisation

**Step 1 — Choose a plan:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Create your Verato account                                     │
├──────────────────────────┬──────────────────────────────────────┤
│  Individual              │  Team                                │
│                          │                                      │
│  Just you                │  You + colleagues                    │
│  1 login                 │  Unlimited logins                    │
│  1 Slack workspace       │  1 shared Slack workspace            │
│                          │  Invite colleagues by email          │
│  [Get started →]         │  [Get started →]                     │
└──────────────────────────┴──────────────────────────────────────┘
```

**Step 2 — Create account:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Your details                                                   │
├─────────────────────────────────────────────────────────────────┤
│  Your name     [Sarah K.                     ]                  │
│  Email         [sarah@acmecorp.com           ]                  │
│  Password      [••••••••••                   ]                  │
│  Org name      [Acme Corp                    ]                  │
│                                          [Create account →]     │
└─────────────────────────────────────────────────────────────────┘
```

API call: `POST /api/v1/auth/register/ {name, email, password, plan, org_name}`
Returns: JWT tokens → redirect to `/onboarding/connect-slack`

---

### Screen 2 — Invite Colleagues (Team plan only)

**Route:** `/settings/team`
**User:** Org Admin
**Access:** Only users with `is_org_admin=True` see the invite form

```
┌─────────────────────────────────────────────────────────────────┐
│  Team members                          [+ Invite colleague]     │
├───────────────────────────┬─────────────┬───────────────────────┤
│  Name                     │  Email      │  Status               │
├───────────────────────────┼─────────────┼───────────────────────┤
│  Sarah K. (you)           │  sarah@...  │  Admin                │
│  Tom R.                   │  tom@...    │  Active               │
│  Maya L.                  │  maya@...   │  Pending invite       │
└───────────────────────────┴─────────────┴───────────────────────┘

[+ Invite colleague]
┌────────────────────────────────────────┐
│  Email  [colleague@acmecorp.com ]      │
│                        [Send invite →] │
└────────────────────────────────────────┘
```

API call: `POST /api/v1/auth/invite/ {email}`
Sends email with link: `APP_BASE_URL/invite/?token={token}`

**Colleague receives email:**

```
Subject: You've been invited to join Acme Corp on Verato

Hi,

Sarah K. has invited you to join Acme Corp on Verato — the
accountability layer for your meetings.

Click here to create your account (expires in 7 days):
https://app.verato.app/invite/?token=abc123...

Verato · Unsubscribe
```

**Colleague accepts:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Join Acme Corp on Verato                                       │
├─────────────────────────────────────────────────────────────────┤
│  Invited as: tom@acmecorp.com                                   │
│  Organisation: Acme Corp                                        │
│                                                                 │
│  Your name     [Tom R.                       ]                  │
│  Password      [••••••••••                   ]                  │
│                                              [Join →]           │
└─────────────────────────────────────────────────────────────────┘
```

API calls:
1. `GET /api/v1/auth/invite/validate/?token=abc123` → `{email, org_name}`
2. `POST /api/v1/auth/invite/accept/ {token, name, password}` → JWT tokens

---

### Screen 3 — Connect Slack (Onboarding step)

**Route:** `/onboarding/connect-slack`
**User:** Org Admin
**Purpose:** Connect the organisation's Slack workspace so nudges can be sent

```
┌─────────────────────────────────────────────────────────────────┐
│  Connect your Slack workspace                                   │
│  Step 1 of 4                                                    │
├─────────────────────────────────────────────────────────────────┤
│  Verato sends Slack DMs to commitment owners before deadlines.  │
│  Connect your workspace to enable nudges.                       │
│                                                                 │
│            [Add to Slack]                                       │
│                                                                 │
│  [Skip for now — connect later from Settings]                   │
└─────────────────────────────────────────────────────────────────┘
```

"Add to Slack" button → `GET /api/v1/slack/oauth/start/`
→ Slack OAuth consent screen
→ Callback: `GET /api/v1/slack/oauth/callback/`
→ Bot token stored in `org.settings['slack_token']`
→ Redirect to `/onboarding/link-slack-id`

Each team member links their own Slack user ID:

```
┌─────────────────────────────────────────────────────────────────┐
│  Link your Slack account                                        │
├─────────────────────────────────────────────────────────────────┤
│  Your Slack user ID is used to send you direct messages.       │
│  Find it in Slack: click your name → Copy member ID            │
│                                                                 │
│  Slack user ID  [U01234ABCDE              ]                     │
│                                              [Save →]           │
└─────────────────────────────────────────────────────────────────┘
```

API call: `POST /api/v1/persons/{id}/link-slack/ {slack_user_id}`

---

### Screen 4 — CoS Command Centre (Dashboard)

**Route:** `/dashboard`
**User:** Chief of Staff

```
┌─────────────────────────────────────────────────────────────────┐
│  Verato            Week of 28 Apr 2026      [+ Upload]          │
├──────────┬──────────┬──────────┬────────────────────────────────┤
│    4     │    7     │   18     │   29                           │
│  Overdue │  At Risk │ On Track │  Total active                  │
├──────────┴──────────┴──────────┴────────────────────────────────┤
│  Needs attention                          [Filter ▾]  [Sort ▾] │
├─────────────────────────────────────────────────────────────────┤
│  ● Q2 board deck — pricing       Sarah K.   Apr 30  OVERDUE 2d  │
│    Q2 planning · Apr 22                             [Escalate]  │
├─────────────────────────────────────────────────────────────────┤
│  ○ Engineering lead hiring brief  Tom R.    May 5   AT RISK     │
│    Nudge sent 9hrs ago · No response                [Chase]     │
├─────────────────────────────────────────────────────────────────┤
│  · Product roadmap v2 draft       Maya L.   May 8   ON TRACK    │
│    Updated 1 day ago                                            │
└─────────────────────────────────────────────────────────────────┘
```

API: `GET /api/v1/dashboard/` → `{overdue, at_risk, on_track, total_active}`

---

### Screen 5 — Commitment Detail

**Route:** `/commitments/:id`

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Back to dashboard                                            │
│  Q2 board deck — pricing section                    [OVERDUE]   │
├─────────────────────────────────────────────────────────────────┤
│  Owner      Sarah K. — CFO                                      │
│  Deadline   Thursday 30 Apr 2026  (2 days overdue)              │
│  Source     Q2 planning · 22 Apr                                │
│  Confidence 0.94                                                │
├─────────────────────────────────────────────────────────────────┤
│  Original quote                                                 │
│  "I'll have the pricing section of the board deck to you by     │
│   end of Thursday — it'll include the EMEA scenarios."          │
├─────────────────────────────────────────────────────────────────┤
│  Actions                                                        │
│  [Send Slack nudge]  [Mark delivered]  [Defer]  [Cancel]        │
├─────────────────────────────────────────────────────────────────┤
│  History                                                        │
│  Apr 22 14:31  Extracted from Q2 planning (confidence 0.94)     │
│  Apr 22 14:45  Confirmed by CoS → status: Active               │
│  Apr 29 09:00  Slack nudge sent to Sarah K.                     │
│  Apr 30 09:00  Deadline passed → Overdue (auto-escalated)       │
└─────────────────────────────────────────────────────────────────┘
```

---

### Screen 6 — Prior Commitments Import (Onboarding)

**Route:** `/onboarding/import`

```
┌─────────────────────────────────────────────────────────────────┐
│  Import your existing commitments                               │
│  Step 2 of 4                                                    │
├─────────────────────────────────────────────────────────────────┤
│  Drop your file here (.csv · .xlsx · .docx · .txt · .md)       │
│  ─── or ────────────────────────────────────────────────────    │
│  [ Paste your action item list here...                   ]      │
│                                          [Extract items →]      │
│  [Skip this step — I'll start fresh]                            │
└─────────────────────────────────────────────────────────────────┘
```

---

### Screen 7 — Upload & Extraction Review

**Route:** `/meetings/upload` → `/meetings/:id/review`

```
┌─────────────────────────────────────────────────────────────────┐
│  Q2 Planning · 22 Apr                          6 found          │
├────────────────────────────────────────┬────────┬──────────────┤
│  Sarah will send pricing deck by Thursday  │  0.94  │ [✓]  [✗] │
│  Tom to share hiring brief with HR         │  0.81  │ [✓]  [✗] │
│  Finance to update Q2 forecast             │  0.73⚠ │ [✓]  [✗] │
├────────────────────────────────────────┴────────┴──────────────┤
│  [Confirm all above 0.80 →]              [Review one by one →]  │
└─────────────────────────────────────────────────────────────────┘
```

---

### Screen 8 — Slack Nudge (owner-facing, no login)

**Delivery:** Slack DM to commitment owner

```
Verato

Hi Tom — a quick check-in on a commitment from the Engineering
standup on 24 Apr:

  "Share the hiring brief with HR before end of Friday"
  Due: Friday 2 May

How's it looking?

  ✅  Done — mark as delivered
  📅  Delayed — set a new date
  🚫  Blocked — let me know why
```

Button responses:
- **Done** → DELIVERED; CoS notified
- **Delayed** → DEFERRED; deadline updated; risk score reset
- **Blocked** → AT_RISK; CoS notified immediately

---

### Screen 9 — Weekly Digest Email

**Delivery:** Monday 07:00 UTC via SendGrid

```
Subject: Your commitment digest — week of 28 Apr

3 commitments need attention before your Monday leadership call.
Sarah's board deck is 2 days overdue. Tom's hiring brief has had
no response since Friday.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OVERDUE
● Sarah K. — Q2 board deck (pricing)     2 days overdue
● Legal team — EMEA contract review      1 day overdue

AT RISK THIS WEEK
○ Tom R. — Engineering lead hiring brief   Due Fri 2 May

ON TRACK THIS WEEK
· Maya L. — Product roadmap v2 draft      Due Fri 2 May

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Open dashboard]

Verato · Unsubscribe
```

Opening paragraph is AI-generated prose (Gemini Flash), not a templated string.

---

## 11. UX Principles

**1. The CoS is the only user who matters for MVP.**
Every screen is designed for her workflow, her language, and her decision-making context.

**2. Action over information.**
Every view surfaces what to do, not just what is happening. The dashboard shows commitments that need action at the top, with the action button inline.

**3. No new tools for individual contributors.**
Commitment owners never log in. Their entire interaction is a single Slack message. This is a non-negotiable design constraint.

**4. The source quote is sacred.**
Every commitment always shows the original verbatim quote from the transcript. This is the product's credibility anchor.

**5. Zero-friction onboarding.**
A CoS can create an account, import her existing tracker, and have a populated dashboard in under 10 minutes — without contacting sales or waiting for a setup call.

**6. Politically aware framing.**
Escalation options are framed, not raw. "Send Slack nudge" is different from "Escalate to CEO".

---

## 12. Go-To-Market

### Outreach framing

> "Most Chiefs of Staff I speak to say they spend 3–5 hours a week manually tracking what was agreed in meetings and chasing people. We're building a tool that does that automatically. Would you be willing to try it on your real transcripts for a month in exchange for shaping the product?"

### The aha moment

The aha moment is the first time an owner replies "Done" in Slack and the CoS sees it update in real time without having to ask.

### Week 1 onboarding script

1. **Session 1 (30 min, with CoS):** Register account. Connect Slack. Import existing tracker — dashboard populated with real data immediately.
2. **Still in session 1:** Upload 2–3 of last week's transcripts. Review extracted commitments together. Confirm the ones she recognises.
3. **First nudge:** Identify one commitment due in the next 48 hours. Send the Slack nudge manually. Watch together for the reply.
4. **Session 2 (15 min, day 3–4):** Review the dashboard. Check nudge replies. Connect the Zoom webhook.
5. **Week 2 onwards:** Zoom auto-ingest live; weekly digest arriving Monday; CoS reviewing independently.

### Pricing

| Tier | Price | What it covers |
|---|---|---|
| Design partner | Free (3 months) | Full product; weekly check-in; direct roadmap input |
| Standard | £299/month per organisation | Full Phase 1 feature set |
| Growth (Phase 2) | £599/month | Standard + conflict detection + analytics + Teams |
| Enterprise (Phase 3) | Custom | SSO + SCIM + exec dashboards + audit export + SLA |

**Pricing rationale:** A CoS at a scale-up earns £80–120k/year. If Verato saves her 3 hours per week, it saves approximately £6,000–9,000/year in salary time. £299/month is well below procurement approval thresholds — she can expense it without a purchase order.

---

## 13. Integration Surface

| Integration | Purpose | Phase |
|---|---|---|
| Slack (per-org OAuth) | Owner nudges, Done/Delayed/Blocked, CoS alerts | 1 ✓ Built |
| SendGrid (via django-anymail) | Weekly digest email, invite emails | 1 ✓ Built |
| Zoom (webhook) | Auto-ingest transcript when meeting ends | 1 (stretch) |
| Microsoft Teams | Auto-ingest Teams transcripts | 2 |
| Google Meet | Auto-ingest Meet transcripts | 2 |
| Jira / Linear | Push commitments as issues; sync status back | 3 |
| Workday / BambooHR | Sync person/role data | 3 |

---

## 14. Success Metrics

### Phase 1 (Design partner validation)

| Metric | Target | What it proves |
|---|---|---|
| Commitments confirmed per meeting | ≥ 6 | Extraction is finding real commitments |
| Extraction confirmation rate | ≥ 75% | Precision high enough to trust |
| Slack nudge response rate | ≥ 60% | Owners are engaging |
| Commitments delivered via nudge (self-reported) | ≥ 1/partner/month | Core value delivered |
| CoS weekly active | 4 of 4 weeks | Product is sticky |
| Time to first nudge (from registration) | < 1 week | Onboarding is frictionless |

### Phase 2 (Revenue validation)

| Metric | Target |
|---|---|
| Paying customers | 5 by Month 4 |
| Monthly churn | < 5% |
| NPS from CoS users | ≥ 50 |
| Expansion: Growth tier conversions | 2 by Month 6 |

---

*End of document. Version 0.3 — Phase 1 backend complete, 264 tests passing. Frontend to be generated with Google AI Studio (Phase 3).*
