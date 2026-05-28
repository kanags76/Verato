# What to Expect in V2

Verato v1 proved the core idea — and then some. AI reads your meeting transcripts, extracts every commitment, and nudges owners before things slip. Meetings flow in automatically from Google Meet and Zoom. Slack and Gmail replies are parsed automatically. Your team can delegate ownership and receive personal notifications.

V2 is about intelligence, not plumbing. The pipeline is built. Now Verato needs to tell you *why* things are at risk, not just *that* they are. Several of these features are already live.

---

## 1. Strategic Initiatives — Already Live

You define your key initiatives — Q3 Product Launch, Board Prep, Hiring Plan — by promoting any tag to a Strategic Initiative with a description. Verato groups all commitments underneath them and gives you:

- Per-initiative commitment counts by status: Active · At Risk · Escalated · Done
- An AI-generated 2–3 sentence health summary per initiative, written for a CoS:

> *"The Product Launch initiative has 8 active commitments. Marketing has 2 at-risk items with deadlines in the next 3 days. Engineering is on track."*

The summary only regenerates when something has actually changed since it was last generated — no unnecessary AI calls. You can also prompt Verato to auto-tag any commitment with suggestions from your existing tag library in one click.

**How to use it:** Add tags to commitments as you confirm them. Once a theme emerges, promote the tag to an Initiative from the Initiatives screen and add a description. The AI summary populates automatically.

---

## 2. Risk Score Breakdown — Already Live

V1 showed each commitment's risk score (0–100) and used it to sort the dashboard. The score is now fully transparent — every commitment shows *why* it scored that way:

- **Deadline proximity (50%)** — how many days remain, with clear labels (Due today / Due in 3 days / Overdue by N days)
- **Owner track record (35%)** — the owner's historical delivery rate across all their commitments
- **Update recency (15%)** — how many days since any activity was logged

This turns the risk score from a black box into a coaching tool. You can see at a glance whether a score is driven by the owner's history or just time pressure.

---

## 3. Ambiguous Replies — Already Improved

When an owner's reply can't be parsed as done / deferred / blocked, Verato no longer silently swallows it. The CoS receives an immediate notification that includes:

- A clear message: *"Action owner replied — I was unable to mark a status. Marked for your review."*
- The owner's full reply text, verbatim
- A link directly to the commitment history where the full reply is also recorded

Every reply either resolves automatically or lands in front of the CoS with full context. Nothing falls through the cracks.

---

## 4. AI Transparency and Eval Foundation — Already Live

Every Gemini call Verato makes — transcript extraction, reply parsing, tag suggestion, initiative summaries, weekly digest — is now logged in full. Each log entry captures the prompt sent, the response received, how long it took, whether it succeeded, and which meeting or commitment triggered it.

This is the foundation for:
- **Prompt management** — all AI prompts are editable in the admin panel without a code deploy
- **Quality tracking** — see how each prompt is performing over time
- **Eval harness** — regression testing new prompt versions against historical inputs and expected outputs

---

## 5. Verato Tells You Why Something Is Slipping — Coming Next

A date change is not the same as a blockade. When an owner replies saying "I'm still waiting on John's team to hand over the API keys," Verato will flag this as a **Cross-Functional Blockade** — highlight it on the dashboard, name the blocking team, and surface it to the CoS as something requiring their intervention.

This is the difference between tracking commitments and managing the politics around them.

---

## 6. Department Health and Commitment Debt — Coming Next

V1 shows delivery rates per individual. V2 will aggregate this into a Department Health view — which teams are consistently hitting deadlines and which are bottlenecked, across the last 2 weeks, month, and quarter.

It will also track Commitment Debt: if a VP consistently extends every deadline by 2 days, week after week, Verato flags them as a chronic under-estimator. This gives the CoS the context to adjust timelines in planning, not in the debrief.

---

## 7. More Meeting Sources — Coming Next

Google Meet and Zoom are already connected. V2 extends this to tl;dv, Fathom, Granola, and Microsoft Teams. Connect once and every meeting, regardless of platform, flows into Verato automatically.

---

## The Bigger Picture

V1 gave you a commitment tracker that removes the manual work. V2 gives you a CoS command centre that removes the guesswork.

By the end of V2, Verato should feel like a Chief of Staff's second brain — one that attends every meeting silently, remembers every promise, reads between the lines of every reply, and puts only the decisions that genuinely need human judgement in front of you.

---

*Verato V2 — In Progress*
