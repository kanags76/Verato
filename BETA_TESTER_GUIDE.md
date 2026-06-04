# Verato — Beta Tester Guide

**What is Verato?**
Verato is your Chief of Staff's command centre. It automatically extracts every commitment made in meetings, assigns it an owner, tracks the deadline, scores how at-risk it is, and nudges the owner before it slips. No more chasing people or losing track of what was promised.

---

## Getting Started

**Step 1 — Create your account**
Go to the app URL and click **Register**. Enter your name, email, and password. You will receive a verification email — click the link to activate your account. This creates your organisation in Verato — you are the admin.

**Step 2 — Complete the onboarding flow**
After activating your account, Verato walks you through a two-step setup:
- **Connect Slack** — Authorise Verato to send nudge DMs to commitment owners. You can skip this and connect later from Settings.
- **Import your existing tracker** — Upload a spreadsheet, document, or CSV of existing commitments so Verato can start with your current backlog rather than from zero. You can also paste text directly. Skip if you are starting fresh.

**Step 3 — Connect your calendar and meeting tools**
Go to **Settings** and connect the integrations that apply to your team:
- **Google Calendar** — Verato automatically detects Google Meet calls when they end, pulls the transcript from Drive, and processes it. No upload needed.
- **Zoom** — Once connected, completed cloud recordings trigger processing automatically via webhook.
- **Gmail** — Verato reads replies to nudge emails and updates commitment status automatically.
- **Slack** — Verato sends nudge DMs and reads owners' replies in the thread.

**Step 4 — Upload your first meeting (or let auto-ingest do it)**
If your calendar is connected, Verato will pick up new meetings automatically. You can also click **Upload** from the dashboard to paste a transcript or upload a `.txt`, `.docx`, or `.csv` file. Processing takes 15–30 seconds. The **Import Tasks** button on the dashboard lets you import from an existing tracker at any time, not just during onboarding.

**Step 5 — Review and confirm commitments**
After processing, go to the meeting and review the extracted commitments. Each one shows the owner, deadline, and a confidence score. Confirm the ones that look right, edit any that need fixing (owner, deadline, wording), and reject anything that isn't actually a commitment.

---

## Core Features to Test

**Dashboard**
Your main view. Shows commitments grouped by status: Overdue, At Risk, On Track. Filter by priority, tag, or owner. Click any commitment to open the detail view.

**Commitment Detail**
Full view of a single commitment — the original text, normalised version, owner, deadline, risk score, and full history of every action taken. You can reassign the owner, change the deadline, escalate, resolve (done / deferred / cancelled), or reopen it.

**Import Tasks**
Available from the **Import Tasks** button on the dashboard at any time. Upload a spreadsheet, document, or CSV of existing commitments and Verato will extract them with AI just like a meeting transcript. Useful for migrating your current backlog on day one or importing a batch of commitments from an offline source.

**Manual Nudge**
On any commitment, click **Nudge**. Choose your method — Slack DM, Email, Phone, In Person. If Gmail is connected, email sends directly from your Gmail account. All nudges are logged in the commitment history so there is a full record.

**Log Manual Update**
On any commitment, use **Log Update** to record a response you received outside the system — a verbal update in a meeting, a WhatsApp message, a note from a call. The update is saved to the commitment history with a timestamp, keeping the full paper trail in one place.

**Automatic Nudges with Reply Parsing**
Verato sends automatic nudge DMs via Slack and emails via Gmail on a schedule. When an owner replies — "done", "pushing to next week", "I'm blocked on X" — Verato reads the reply once daily at 08:00 UTC, parses the intent with Gemini AI, and updates the commitment status automatically. If the reply is ambiguous, the CoS receives a notification with the full reply text and can decide what to do.

**Slack Interactive Buttons**
Slack nudge DMs include three action buttons the owner can tap directly in Slack: **Done**, **Need more time**, or **Blocked**. Tapping a button updates the commitment instantly — no reply needed.

**Auto-Ingestion (Google Meet + Zoom)**
Once your Google Calendar or Zoom is connected, new meetings flow into Verato automatically:
- Google Meet calls end → Verato finds the transcript in Drive within 15 minutes and processes it
- Zoom cloud recordings complete → webhook fires, Verato processes the recording immediately

Check the **Meetings** list to see the status of each ingested meeting (Pending / Processing / Done / Failed).

**Strategic Initiatives**
Group related commitments under strategic themes — Q3 Product Launch, Board Prep, Hiring Plan, etc. Any tag can be promoted to a Strategic Initiative with a description. The Initiatives view shows per-status commitment counts (Active, At Risk, Escalated, Done) and an AI-generated 2–3 sentence health summary per initiative. The summary only regenerates when commitments have changed since the last one.

**Tags and Auto-tagging**
Every commitment can carry one or more tags. Tags are created inline as you type — no pre-configuration needed. On any commitment, click **Auto-tag** to have Gemini suggest and apply tags from your existing tag library. Admins can rename, merge, promote, or delete tags via the Tags management panel.

**Risk Score Breakdown**
The risk score on each commitment now shows a full breakdown: how much of the score comes from deadline proximity (50%), the owner's historical delivery rate (35%), and how recently the commitment was updated (15%). This turns the score from a black box into an actionable signal.

**Directory**
See everyone who makes commitments in your meetings — they receive nudges but don't need a Verato account. Use the **Add to Directory** button to add someone manually or import your Slack workspace members. Merge duplicate records if the same person appears under two names.

**Delegation**
A CoS can delegate meeting ownership to a colleague (e.g., a senior EA or department lead). Go to **Settings → Delegation** and assign a delegate. They receive an email invitation and an in-app notification. Once accepted, they can manage commitments from meetings assigned to them.

**Meetings**
Full list of all uploaded and auto-ingested meetings with processing status. Click into any meeting to see the transcript, participants, and all commitments extracted from it.

**In-App Notifications**
The bell icon in the top nav shows your personal notification feed:
- When a Slack or Gmail reply comes in on a commitment you own or manage
- When a commitment you created is marked done or deferred
- When someone accepts a delegation invite
- When a meeting finishes processing

**Settings**
- **Slack** — Connect your Slack workspace. Once connected, automatic nudge DMs go to owners on the schedule you set. Slack users can be searched and linked to Person records.
- **Gmail** — Connect your Gmail account. Verato sends nudge emails from your address and reads owner replies automatically.
- **Google Calendar** — Connect your calendar to enable Google Meet auto-ingestion.
- **Zoom** — Connect your Zoom account to enable Zoom recording auto-ingestion.
- **Team** — Invite colleagues, resend or revoke pending invitations.
- **Nudge Schedule** — Set when automatic reminders fire: first nudge (1, 2, or 5 days before deadline), second nudge (24, 48, or 72 hours before), then daily nudges for days +1, +2, +3 overdue. Toggle the whole engine on/off.

---

## What to Look For

Please test and give feedback on:

1. **Onboarding flow** — Does the two-step setup (Slack → Import) feel intuitive for a new user? Is anything confusing or missing?
2. **Extraction quality** — Did Verato find all the real commitments? Did it miss any? Did it pick up anything that wasn't a commitment?
3. **Owner matching** — Did it correctly identify who owns each commitment?
4. **Deadline resolution** — If someone said "by end of Thursday" did it resolve to the right date?
5. **Auto-ingestion** — If your calendar is connected, does the meeting appear and process within 15 minutes of it ending?
6. **Tracker import** — Upload a spreadsheet of existing commitments — does Verato extract them accurately?
7. **Reply parsing** — Reply to a Slack nudge DM or email nudge with "done" or "need another week" — does Verato pick it up correctly the next morning?
8. **Slack buttons** — Tap Done or Need More Time on a Slack nudge — does the commitment update immediately?
9. **Commitment actions** — Confirm, escalate, resolve, reopen — do they feel right?
10. **Log Manual Update** — Log a verbal update you received outside the system — does the history capture it clearly?
11. **Nudge flow** — Does the Slack DM arrive? Does the email send from your Gmail?
12. **Risk score breakdown** — Does the breakdown (deadline / owner track record / recency) match your intuition about why a commitment is at risk?
13. **Strategic Initiatives** — Does grouping commitments by initiative help you see the health of a theme at a glance?
14. **Auto-tag** — Does Gemini's tag suggestion match what you would have chosen manually?
15. **Notifications** — Do in-app notifications appear at the right times for the right people?

---

## Known Limitations (Beta)

- **Slack nudges** require the org admin to connect Slack and enable the nudge engine in Settings first
- **Gmail and Slack reply parsing** runs once daily at 08:00 UTC — not instant; Slack interactive buttons (Done / Need More Time / Blocked) update immediately
- **Google Meet auto-ingest** requires the meeting organiser to have Google Workspace with transcription enabled in Drive; if transcription is off, Verato will detect this and fall back to manual upload
- **Zoom auto-ingest** requires Zoom cloud recording to be enabled on the account
- **Tag management** (rename, merge, delete) is admin-only — regular users can add and view tags
- **Initiative AI summaries** regenerate at most once every 12 hours unless new commitment activity is logged
- The app is in active development — some rough edges expected

---

**Questions or bugs?** Reply directly to this message with what you found. Screenshots are very helpful.
