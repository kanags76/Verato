# Verato — Beta Tester Guide

**What is Verato?**
Verato is your Chief of Staff's command centre. It automatically extracts every commitment made in meetings, assigns it an owner, tracks the deadline, scores how at-risk it is, and nudges the owner before it slips. No more chasing people or losing track of what was promised.

---

## Getting Started

**Step 1 — Create your account**
Go to the app URL and click **Register**. Enter your name, email, and password. This creates your organisation in Verato — you are the admin.

**Step 2 — Upload your first meeting**
Click **Upload** from the dashboard. Paste in a transcript or upload a `.txt`, `.docx`, or `.csv` file. Verato sends it to Gemini AI, which extracts every commitment — who promised what, by when — and brings them back for you to review. This takes 15–30 seconds.

**Step 3 — Review and confirm commitments**
After processing, go to the meeting and review the extracted commitments. Each one shows the owner, deadline, and a confidence score. Confirm the ones that look right, edit any that need fixing (owner, deadline, wording), and reject anything that isn't actually a commitment.

---

## Core Features to Test

**Dashboard**
Your main view. Shows commitments grouped by status: Overdue, At Risk, On Track. Filter by priority, tag, or owner. Click any commitment to open the detail view.

**Commitment Detail**
Full view of a single commitment — the original text, normalised version, owner, deadline, risk score, and full history of every action taken. You can reassign the owner, change the deadline, escalate, resolve (done / deferred / cancelled), or reopen it.

**Manual Nudge**
On any commitment, click **Nudge**. Choose your method — Slack DM, Email, Phone, In Person. If Gmail is connected, email sends directly from your Gmail account. All nudges are logged in the commitment history so there is a full record.

**People**
See everyone in your organisation with their delivery rate and commitment count. Add new people, link them to their Slack account, or merge duplicate records if the same person appears under two names.

**Meetings**
Full list of all uploaded meetings with processing status. Click into any meeting to see the transcript, participants, and all commitments extracted from it.

**Settings**
- **Slack** — Connect your Slack workspace. Once connected, automatic nudge DMs go to owners on the schedule you set.
- **Gmail** — Connect your Gmail account. Verato sends nudge emails from your address and automatically reads the owner's reply — if they say "done" or "pushing to next week", Verato updates the commitment status automatically.
- **Nudge Schedule** — Set when automatic reminders fire: first nudge (1, 2, or 5 days before deadline), second nudge (24, 48, or 72 hours before), then daily nudges for days +1, +2, +3 overdue. Toggle the whole engine on/off.

---

## What to Look For

Please test and give feedback on:

1. **Extraction quality** — Did Verato find all the real commitments? Did it miss any? Did it pick up anything that wasn't a commitment?
2. **Owner matching** — Did it correctly identify who owns each commitment?
3. **Deadline resolution** — If someone said "by end of Thursday" did it resolve to the right date?
4. **Commitment actions** — Confirm, escalate, resolve, reopen — do they feel right?
5. **Nudge flow** — Does the Slack DM arrive? Does the email send from your Gmail?
6. **Risk scoring** — Does the At Risk / Overdue grouping match your intuition about which commitments are in trouble?

---

## Known Limitations (Beta)

- **Slack nudges** require the org admin to connect Slack and enable the nudge engine in Settings first
- **Gmail reply auto-parsing** runs every 30–120 min depending on your org's poll setting — not instant
- **Zoom / Google Meet auto-ingest** not yet built — transcripts must be uploaded manually
- The app is in active development — some rough edges expected

---

**Questions or bugs?** Reply directly to this message with what you found. Screenshots are very helpful.
