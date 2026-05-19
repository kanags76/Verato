# Commitment OS — Product Specification & Key Screens

> **Version:** 0.1 — Design Partner Draft  
> **ICP:** Chief of Staff, Programme Manager  
> **Stack:** Django REST (AWS) · Next.js (GCP) · Gemini 1.5 Pro · PostgreSQL + pgvector

---

## 1. Product Vision

Commitment OS is the accountability layer that sits on top of an organisation's meetings. It extracts every commitment made across all meetings, structures each one with an owner, deadline, and risk score, detects conflicts between meetings, and gives the Chief of Staff and leadership team a real-time view of what was promised, what is at risk, and what needs escalating.

**The one-line pitch:** "Every commitment your organisation makes — tracked, owned, and surfaced before it slips."

---

## 2. The Problem Being Solved

| Today | With Commitment OS |
|---|---|
| Commitments live in meeting notes, memory, and scattered Notion pages | Every commitment is a structured, tracked object |
| Nobody knows what's overdue until the deadline passes | Risk surfaces 48–72 hours before a commitment is at risk |
| Cross-meeting contradictions go unnoticed | Conflicts between meetings are detected and flagged automatically |
| CoS spends hours chasing status updates | Owners get nudged automatically; CoS only steps in when needed |
| Execs have no visibility into commitment health | Dashboard gives real-time accountability view across the org |

---

## 3. Core Value Propositions

### 3.1 Commitment Extraction
AI reads every meeting transcript and extracts all commitments — not just action items, but explicit promises, implicit agreements, and conditional commitments. Each is structured with owner, deadline, type, and confidence score.

### 3.2 Risk & Drift Detection
Every active commitment has a live risk score computed from deadline proximity, owner track record, dependency health, and recency of updates. Commitments surface as amber (at risk) or red (overdue/escalated) before they become a problem.

### 3.3 Cross-Meeting Conflict Detection
When a commitment made in Tuesday's roadmap meeting contradicts one made in Thursday's leadership review, the system flags it. The CoS sees the conflict, the source quotes, and resolution options.

### 3.4 Executive Intelligence Dashboard
A single screen gives the CoS and exec team a live view of all open commitments, their health, and the organisation's 30-day delivery rate — without attending every meeting.

### 3.5 Accountability Nudge Layer
Owners receive Slack/email nudges 48 hours before a deadline. Responses update commitment status automatically. If no response, the CoS is notified with escalation options. No new tool for individual contributors — they respond in Slack.

---

## 4. The Core Loop

```
INGEST → EXTRACT → STRUCTURE → MONITOR → SURFACE → RESOLVE
```

1. **Ingest** — Transcript enters via Zoom webhook, manual upload, or Teams connector
2. **Extract** — Gemini 1.5 Pro identifies all commitment candidates with confidence scores
3. **Structure** — Each commitment becomes a typed object: owner, deadline, status, risk, dependencies
4. **Monitor** — Risk scores recomputed every 6 hours; status transitions trigger notifications
5. **Surface** — CoS dashboard, weekly digest, pre-meeting briefings, escalation queue
6. **Resolve** — Commitments close as delivered, deferred, or cancelled with audit trail

---

## 5. Feature Set — Phased

### Phase 1 (Months 1–3): The Core Loop
*Ship this first. Get design partners running on it by week 6.*

| Feature | Description |
|---|---|
| Transcript ingestion | Upload file or Zoom webhook connector |
| Commitment extraction | Explicit commitments only; AI-suggested, human-confirmed |
| Owner + deadline assignment | AI assigns from participant list; CoS can edit |
| Commitment tracker | List view with status, owner, deadline, risk flag |
| Slack nudges | 48hr pre-deadline DM to owner; response updates status |
| Weekly CoS digest | Monday 07:00 email: overdue, at-risk, due this week |
| Basic dashboard | Summary cards + commitment list |

### Phase 2 (Months 3–6): Intelligence Layer
*After design partner validation. Build these in priority order.*

| Feature | Description |
|---|---|
| Cross-meeting conflict detection | pgvector similarity + Gemini Flash classification |
| Dependency chain tracking | B is blocked on A; A is at risk → B flagged |
| Implicit + conditional commit extraction | Expands extraction beyond explicit statements |
| Teams + Google Meet connectors | Full multi-platform ingestion |
| Pre-meeting briefing | Open commits relevant to today's agenda, auto-generated |
| Escalation logic | CoS notified with framing options when commit goes red |
| Accountability analytics | Delivery rate by person, team, and time period |
| Org-calibrated extraction | System learns this org's commit language from feedback |

### Phase 3 (Months 6–12): Platform Layer
*After £300k ARR. Builds enterprise stickiness.*

| Feature | Description |
|---|---|
| Board / exec reporting view | Commitment health across org for leadership reviews |
| HRIS / PM tool API | Jira, Linear, Workday integration |
| Audit trail export | Legal and governance use case |
| Multi-team / division view | Enterprise orgs with 5+ teams |
| SSO + admin controls | Enterprise security requirements |
| Custom escalation workflows | Configurable per org structure |
| Natural language query | "What have we committed to on EMEA pricing?" |

---

## 6. User Roles

| Role | Access | Primary use |
|---|---|---|
| **Chief of Staff** | Full access — all commitments, analytics, escalation | Daily command centre; weekly digest; escalation decisions |
| **Programme Manager** | Full access within their programme | Track commitments across their workstreams |
| **Executive / Sponsor** | Read-only dashboard for their team's commitments | Weekly health check; escalation recipient |
| **Commitment Owner** | Receives nudges; can update own commitment status | Respond to nudges; mark delivered |
| **Org Admin** | User management, integration config, billing | Setup and configuration |

---

## 7. Key Screens

### Screen 1 — CoS Command Centre (Primary Daily View)

**Route:** `/dashboard`  
**User:** Chief of Staff  
**Purpose:** Single-screen situational awareness — what needs attention today

```
┌─────────────────────────────────────────────────────────────────┐
│  Commitment OS          Week of 28 Apr 2026        [+ Upload]   │
├──────────┬──────────┬──────────┬────────────────────────────────┤
│  4       │  7       │  18      │  68%                           │
│  Overdue │  At Risk │  On Track│  30-day delivery rate          │
├──────────┴──────────┴──────────┴────────────────────────────────┤
│  NEEDS ATTENTION                               Filter ▾  Sort ▾ │
├─────────────────────────────────────────────────────────────────┤
│  ● Q2 board deck — pricing    Sarah K.  Due Apr 30  [OVERDUE 2d]│
│    Source: Q2 planning · Apr 22                    [Escalate →] │
├─────────────────────────────────────────────────────────────────┤
│  ● EMEA contract legal review  Legal    Due May 2   [OVERDUE 1d]│
│    Source: Legal review · Apr 21                   [Escalate →] │
├─────────────────────────────────────────────────────────────────┤
│  ○ Eng lead hiring brief       Tom R.   Due May 5   [AT RISK]   │
│    Nudge sent 9hrs ago · No response               [Chase →]    │
├─────────────────────────────────────────────────────────────────┤
│  ○ Product roadmap v2 draft    Maya L.  Due May 8   [ON TRACK]  │
│    Updated 1 day ago                                            │
├─────────────────────────────────────────────────────────────────┤
│  + 25 more commitments                          [View all →]    │
└─────────────────────────────────────────────────────────────────┘
```

**Key interactions:**
- Click any row → Commitment detail view
- [Escalate] → Opens escalation options modal
- [+ Upload] → Transcript upload flow
- Filter by: status, owner, team, meeting, date range
- Sort by: deadline, risk score, owner

---

### Screen 2 — Commitment Detail View

**Route:** `/commitments/:id`  
**User:** Chief of Staff  
**Purpose:** Full context on a single commitment; take action

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Back to dashboard                                            │
│                                                                 │
│  Q2 board deck — pricing section           [OVERDUE] [⚠ CONFLICT]│
├─────────────────────────────────────────────────────────────────┤
│  Owner        Sarah K. — CFO                                    │
│  Deadline     Thu 30 Apr 2026 (2 days overdue)                  │
│  Confidence   0.94 — Explicit commit                            │
│  Source       Q2 planning · Apr 22 · 14:31                      │
├─────────────────────────────────────────────────────────────────┤
│  ORIGINAL QUOTE                                                 │
│  "I'll have the pricing section of the board deck to you by     │
│   end of Thursday — it'll include the EMEA scenarios."          │
├─────────────────────────────────────────────────────────────────┤
│  ⚠ CONFLICT DETECTED                                            │
│  Contradicts commitment from Apr 18 pricing meeting:           │
│  "The deck won't be ready until after the May review."          │
│  → [View conflict] [Resolve]                                    │
├─────────────────────────────────────────────────────────────────┤
│  ESCALATION OPTIONS                                             │
│  [Gentle nudge via Slack]  [Flag as urgent]  [Escalate to CEO] │
│  [Mark as deferred]        [Mark as cancelled]                  │
├─────────────────────────────────────────────────────────────────┤
│  HISTORY                                                        │
│  Apr 22 14:31  Commitment extracted (confidence 0.94)          │
│  Apr 22 14:45  Confirmed by CoS                                 │
│  Apr 29 09:00  Nudge sent to Sarah K. via Slack                 │
│  Apr 30 09:00  Status → OVERDUE (no response)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### Screen 3 — Transcript Ingestion & Extraction Review

**Route:** `/meetings/upload` + `/meetings/:id/review`  
**User:** Chief of Staff  
**Purpose:** Upload transcript; review and confirm extracted commitments before they enter tracker

```
┌─────────────────────────────────────────────────────────────────┐
│  Upload Meeting Transcript                                      │
├─────────────────────────────────────────────────────────────────┤
│  [  Drop transcript file or paste text here  ]                  │
│  Supported: .txt, .vtt, .srt, .docx, or paste raw text         │
│                                    [Process meeting →]          │
└─────────────────────────────────────────────────────────────────┘

  Processing... Gemini 1.5 Pro analysing 14,200 words ████░░  73%

┌─────────────────────────────────────────────────────────────────┐
│  Q2 Planning · Apr 22 · Processed                [6 found] ✓   │
├────────────────────────────────────────────┬────────┬──────────┤
│  Commitment                                │ Conf.  │ Action   │
├────────────────────────────────────────────┼────────┼──────────┤
│  Sarah will send pricing deck by Thursday  │ ●0.94  │ [✓] [✗] │
│  EXPLICIT · Owner: Sarah K. · Due: Apr 30  │        │          │
├────────────────────────────────────────────┼────────┼──────────┤
│  Tom to share hiring brief with HR         │ ●0.81  │ [✓] [✗] │
│  EXPLICIT · Owner: Tom R. · Due: May 2     │        │          │
├────────────────────────────────────────────┼────────┼──────────┤
│  Revisit EMEA pricing before May           │ ◐0.52  │ [✓] [✗] │
│  IMPLICIT · Owner: unclear · Review needed │        │          │
├────────────────────────────────────────────┼────────┼──────────┤
│  Maya to have roadmap draft by end of wk   │ ●0.88  │ [✓] [✗] │
│  EXPLICIT · Owner: Maya L. · Due: May 8    │        │          │
├────────────────────────────────────────────┴────────┴──────────┤
│  [Confirm all high-confidence →]          [Review individually] │
└─────────────────────────────────────────────────────────────────┘
```

**Confidence legend:**
- `● 0.80+` — High confidence, auto-confirm safe
- `◐ 0.50–0.79` — Medium confidence, review recommended  
- `○ <0.50` — Low confidence, manual review required

---

### Screen 4 — Analytics Dashboard

**Route:** `/analytics`  
**User:** Chief of Staff, Executive sponsor  
**Purpose:** Accountability patterns, delivery trends, person-level insights

```
┌─────────────────────────────────────────────────────────────────┐
│  Accountability Analytics         Apr 2026    [Export PDF]      │
├─────────────┬───────────────────────────────────────────────────┤
│  30d Rate   │  Delivery rate trend (12 weeks)                   │
│  68%  ↓4%  │  ████████████████░░░░░░░░░░░░░░░░░░░░░░  68%     │
│             │  Jan    Feb    Mar    Apr                          │
├─────────────┴───────────────────────────────────────────────────┤
│  BY PERSON                         │  BY TEAM                   │
│  Sarah K.    ████████░░  82%  12   │  Engineering  ██████  74% │
│  Tom R.      ████░░░░░░  45%   9   │  Legal        ████░░  55% │
│  Maya L.     █████████░  91%   7   │  Product      █████░  68% │
│  Legal team  █████░░░░░  55%  11   │  Operations   ████░░  61% │
├────────────────────────────────────┴────────────────────────────┤
│  COMMITMENT SOURCES (by meeting type)                           │
│  Leadership review  ████████████████  38 commits · 72% rate    │
│  Project standups   ████████████░░░░  24 commits · 58% rate    │
│  1:1s               ████████░░░░░░░░  18 commits · 88% rate    │
└─────────────────────────────────────────────────────────────────┘
```

---

### Screen 5 — Monday Morning CoS Digest (Email)

**Delivery:** Monday 07:00 via SendGrid  
**User:** Chief of Staff  
**Purpose:** Weekly situational awareness without opening the app

```
Subject: Commitment OS — Your week ahead · Mon 28 Apr

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THIS WEEK'S RISK SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3 commitments from last week's leadership review are still open
with deadlines in the next 4 days. Sarah's board deck is overdue.
The EMEA contract review has had no update since Apr 18.

NEEDS IMMEDIATE ACTION
━━━━━━━━━━━━━━━━━━━━━━
● Sarah K. — Q2 board deck pricing    OVERDUE 2 days   [Act now]
● Legal — EMEA contract review        OVERDUE 1 day    [Act now]

AT RISK THIS WEEK
━━━━━━━━━━━━━━━━━
○ Tom R. — Hiring brief to HR         Due May 5        [Chase]
○ Finance — Q2 forecast update        Due May 6        [Chase]

CONFLICTS TO RESOLVE
━━━━━━━━━━━━━━━━━━━━
⚠ EMEA pricing: contradiction between Apr 18 and Apr 22 meetings

30-DAY DELIVERY RATE: 68%  ↓4% from last month

[Open dashboard →]        [View all commitments →]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Commitment OS · Unsubscribe
```

---

### Screen 6 — Conflict Review View

**Route:** `/conflicts`  
**User:** Chief of Staff  
**Purpose:** Review and resolve cross-meeting contradictions

```
┌─────────────────────────────────────────────────────────────────┐
│  Conflicts requiring review                    2 unresolved     │
├─────────────────────────────────────────────────────────────────┤
│  ⚠ CONTRADICTION — EMEA Pricing               Confidence: 0.87 │
├─────────────────────────────────────────────────────────────────┤
│  Apr 18 — Pricing committee                                     │
│  "The deck won't be ready until after the May board review."    │
│  Owner: Sarah K.                                                │
│                                                                 │
│  vs.                                                            │
│                                                                 │
│  Apr 22 — Q2 planning                                           │
│  "I'll have the pricing section ready by end of Thursday."      │
│  Owner: Sarah K.                                                │
├─────────────────────────────────────────────────────────────────┤
│  [Apr 22 supersedes Apr 18]  [Apr 18 still stands]  [Dismiss]  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. UX Principles

1. **CoS first, always** — Every screen is optimised for the Chief of Staff's daily workflow, not the engineer's mental model
2. **Action over information** — Every view surfaces what to do, not just what is happening
3. **No new tools for ICs** — Commitment owners never need to log in; they respond in Slack
4. **Accuracy over volume** — Better to surface 10 high-confidence commitments than 40 uncertain ones
5. **Politically aware** — Escalation options are framed, not raw; the product understands org dynamics

---

## 9. Integration Surface

| Integration | Purpose | Phase |
|---|---|---|
| Zoom (webhook) | Auto-ingest transcripts on meeting end | 1 |
| Slack (Bolt SDK) | Owner nudges, status updates, CoS alerts | 1 |
| SendGrid | Weekly digest, escalation emails | 1 |
| Microsoft Teams | Auto-ingest Teams meeting transcripts | 2 |
| Google Meet | Auto-ingest Meet transcripts | 2 |
| Jira / Linear | Push committed deliverables as issues | 3 |
| Workday / BambooHR | Sync person/role data | 3 |

---

*End of document — feed into VS Code + Claude for implementation context*
