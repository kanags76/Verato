"""
Verato — comprehensive seed data for frontend testing.

Run (purge first):
  CLEAR=1 python manage.py shell < scripts/seed_test_data.py

Run (add on top of existing):
  python manage.py shell < scripts/seed_test_data.py

Story: TwoCents Capital is a fintech scale-up mid-Series-A fundraise.
       Q2 planning, engineering hiring push, and a product launch are
       all in flight simultaneously.  Eight meetings, eight people, 25
       commitments with a full audit trail so every screen has rich data.

Narrative threads (same topic appears across multiple meetings):
  A — Series A fundraise   (board → investor-prep → standup → pending)
  B — Engineering hiring   (Q2-kickoff → eng-deep-dive → standup → pending)
  C — Security & infra     (eng-deep-dive → product-review)
  D — Product launch       (product-review → standup → pending)
  E — BD pipeline          (Q2-kickoff → bd-meeting → pending)
  F — Operations / OKRs    (Q2-kickoff → board → standup)

Latest meeting (1 day ago) has confirmed=False on all participants
and all its commitments are pending_review — demonstrating the
extraction-review + participant-validation flow.
"""
import os
from datetime import date, datetime, timedelta
from django.utils import timezone
from apps.accounts.models import User, Organisation, Person
from apps.meetings.models import Meeting, MeetingParticipant, MeetingTopic
from apps.commitments.models import (
    Commitment, CommitmentTag, CommitmentEvent,
    EscalationEvent, ExtractionFeedback,
)
from apps.notifications.models import NudgeLog

today = date.today()
now   = timezone.now()

CLEAR = os.environ.get('CLEAR', '').strip() == '1'


# ── Helpers ───────────────────────────────────────────────────────────────────

def aware(d):
    return timezone.make_aware(datetime.combine(d, datetime.min.time()))

def days_ago(n):
    return today - timedelta(days=n)

def days_from_now(n):
    return today + timedelta(days=n)

def t_ago(days=0, hours=0):
    return now - timedelta(days=days, hours=hours)


# ── Org ───────────────────────────────────────────────────────────────────────

org, _ = Organisation.objects.get_or_create(
    slug='twocents',
    defaults={'name': 'TwoCents Capital', 'plan': 'team'},
)
print(f"Org: {org.name}")

# ── User ──────────────────────────────────────────────────────────────────────

user = (
    User.objects.filter(is_org_admin=True).first()
    or User.objects.filter(is_superuser=True).first()
    or User.objects.first()
)
if user is None:
    raise RuntimeError("No users found in DB. Run manage.py createsuperuser first.")
user.organisation = org
user.is_org_admin  = True
user.save()
print(f"User: {user.email}")

# ── Purge ────────────────────────────────────────────────────────────────────

if CLEAR:
    NudgeLog.objects.filter(commitment__organisation=org).delete()
    CommitmentEvent.objects.filter(commitment__organisation=org).delete()
    EscalationEvent.objects.filter(commitment__organisation=org).delete()
    ExtractionFeedback.objects.filter(organisation=org).delete()
    Commitment.objects.filter(organisation=org).delete()
    CommitmentTag.objects.filter(organisation=org).delete()
    MeetingTopic.objects.filter(organisation=org).delete()
    MeetingParticipant.objects.filter(meeting__organisation=org).delete()
    Meeting.objects.filter(organisation=org).delete()
    Person.objects.filter(organisation=org).exclude(user=user).delete()
    print("Cleared all data for org.")


# ── People ────────────────────────────────────────────────────────────────────
# delivery_rate drives risk score colour and People page bars.
# Tom Bradley is the "problem child" — low delivery, high avg_days_late.

people_data = [
    # name, email, role, delivery_rate, avg_days_late, total_commitments, meeting_count
    ('Sarah Chen',    'sarah@twocents.ai',   'CEO',                    0.92, 0.5,  28, 14),
    ('James Okafor',  'james@twocents.ai',   'CTO',                    0.68, 3.9,  34, 10),
    ('Priya Nair',    'priya@twocents.ai',   'Chief Product Officer',  0.85, 1.6,  22,  9),
    ('Tom Bradley',   'tom@twocents.ai',     'VP Sales',               0.52, 7.2,  26,  8),
    ('Elena Vasquez', 'elena@twocents.ai',   'VP Engineering',         0.88, 0.8,  19,  8),
    ('Marcus Hill',   'marcus@twocents.ai',  'CFO',                    0.78, 2.1,  16,  7),
    ('Aisha Patel',   'aisha@twocents.ai',   'Head of Talent',         0.83, 1.2,  12,  5),
]

people = {}
for name, email, role, dr, adl, tc, mc in people_data:
    p, created = Person.objects.get_or_create(
        organisation=org, email=email,
        defaults={
            'name': name, 'role': role,
            'delivery_rate': dr, 'avg_days_late': adl,
            'total_commitments': tc, 'meeting_count': mc,
        },
    )
    if not created:
        p.name = name; p.role = role; p.delivery_rate = dr
        p.avg_days_late = adl; p.total_commitments = tc; p.meeting_count = mc
        p.save()
    people[name] = p
    print(f"  Person: {name} ({role}) — delivery {int(dr*100)}%")

# CoS — find the person already linked to this user (survives CLEAR), or create one
cos = Person.objects.filter(user=user).first()
if cos is None:
    cos = Person.objects.create(
        organisation=org, email=user.email,
        name='Kiran Nags', role='Chief of Staff',
        user=user, delivery_rate=0.95,
        total_commitments=10, meeting_count=16,
    )
else:
    cos.organisation = org; cos.name = 'Kiran Nags'
    cos.role = 'Chief of Staff'; cos.delivery_rate = 0.95
    cos.total_commitments = 10; cos.meeting_count = 16
    cos.save()
people['Kiran Nags'] = cos


# ── Tags ─────────────────────────────────────────────────────────────────────
# Tags are the shared vocabulary across meetings — clicking one tag on the
# dashboard filters across multiple meetings and owners.

tag_labels = [
    'series a',       # fundraise thread
    'board prep',     # board comms
    'hiring',         # hiring thread
    'engineering',    # tech delivery
    'security',       # infra/security
    'product launch', # launch thread
    'product',        # product work
    'sales',          # BD/sales
    'partnerships',   # BD partnerships
    'legal',          # legal/contracts
    'finance',        # finance/CFO thread
    'okrs',           # Q2 planning
    'data room',      # investor due diligence
    'onboarding',     # customer/employee onboarding
    'analytics',      # reporting/dashboards
]

tags = {}
for label in tag_labels:
    t, _ = CommitmentTag.objects.get_or_create(organisation=org, label=label)
    tags[label] = t


# ── Meetings ──────────────────────────────────────────────────────────────────
# 8 meetings spanning 8 weeks.  The most recent one (1 day ago) has all
# participants unconfirmed and all commitments pending_review — exactly what
# the extraction-review + link-participants screens show.

def make_meeting(title, n_ago, mtype, platform, summary, participant_names, confirmed=True):
    m, _ = Meeting.objects.get_or_create(
        organisation=org, title=title,
        defaults={
            'occurred_at':       aware(days_ago(n_ago)),
            'meeting_type':      mtype,
            'platform':          platform,
            'processing_status': 'complete',
            'processed_at':      aware(days_ago(n_ago)),
            'summary':           summary,
        },
    )
    for pname in participant_names:
        if pname in people:
            MeetingParticipant.objects.get_or_create(
                meeting=m, person=people[pname],
                defaults={'speaker_label': pname, 'confirmed': confirmed},
            )
    return m


m_board = make_meeting(
    'Board Meeting — Q1 Review', 56, 'board', 'upload',
    'Reviewed Q1 financial results and approved Series A timeline. '
    'Board requested updated data room by end of April. '
    'Engineering and product milestones presented; hiring plan approved.',
    ['Sarah Chen', 'James Okafor', 'Marcus Hill', 'Kiran Nags'],
)
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_board, label='q1 financials',    defaults={'confidence': 0.97})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_board, label='series a timeline',defaults={'confidence': 0.95})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_board, label='board governance', defaults={'confidence': 0.90})

m_q2kick = make_meeting(
    'Q2 All-Hands Kickoff', 42, 'leadership', 'upload',
    'Full leadership team aligned on Q2 OKRs. '
    'Key themes: Series A close, senior engineering hiring, product launch in July. '
    'Tom Bradley presented BD pipeline; 3 enterprise pilots identified as Q2 targets.',
    ['Sarah Chen', 'James Okafor', 'Priya Nair', 'Tom Bradley', 'Elena Vasquez', 'Marcus Hill', 'Aisha Patel', 'Kiran Nags'],
)
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_q2kick, label='q2 okrs',         defaults={'confidence': 0.96})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_q2kick, label='hiring plan',     defaults={'confidence': 0.94})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_q2kick, label='product strategy',defaults={'confidence': 0.91})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_q2kick, label='enterprise sales',defaults={'confidence': 0.88})

m_investor = make_meeting(
    'Series A Due Diligence Prep', 28, 'leadership', 'upload',
    'Sarah, Marcus and Kiran walked through investor Q&A pack. '
    'Financial model needs a revenue sensitivity analysis added. '
    'Data room structure finalised; target close in 6 weeks.',
    ['Sarah Chen', 'Marcus Hill', 'Kiran Nags'],
)
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_investor, label='data room',           defaults={'confidence': 0.98})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_investor, label='financial model',     defaults={'confidence': 0.96})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_investor, label='investor q&a',        defaults={'confidence': 0.92})

m_eng = make_meeting(
    'Engineering Architecture Deep Dive', 21, 'project', 'upload',
    'James and Elena reviewed the migration plan for moving production to eu-west-2. '
    'Security audit scoped and assigned. '
    'Interview pipeline for 3 senior backend roles reviewed — offers expected by end of month.',
    ['James Okafor', 'Elena Vasquez', 'Aisha Patel', 'Kiran Nags'],
)
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_eng, label='system architecture', defaults={'confidence': 0.95})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_eng, label='security audit',      defaults={'confidence': 0.93})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_eng, label='hiring pipeline',     defaults={'confidence': 0.89})

m_product = make_meeting(
    'Product Roadmap — Q2 Review', 14, 'team', 'upload',
    'Priya walked through the updated Q2 roadmap with engineering. '
    'Design partner interview programme approved — 5 sessions in June. '
    'API rate limiting and new onboarding flow are the two hard dependencies for July launch.',
    ['Priya Nair', 'James Okafor', 'Elena Vasquez', 'Kiran Nags'],
)
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_product, label='product roadmap',        defaults={'confidence': 0.97})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_product, label='design partner programme',defaults={'confidence': 0.93})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_product, label='launch readiness',        defaults={'confidence': 0.91})

m_standup = make_meeting(
    'Weekly Leadership Sync', 7, 'leadership', 'upload',
    'Series A update: Marcus confirmed data room 80% complete, investor meetings scheduled. '
    'Hiring: 2 offers out, 1 accepted. '
    'Tom flagged that EnterpriseX deal needs term sheet before end of week.',
    ['Sarah Chen', 'James Okafor', 'Priya Nair', 'Tom Bradley', 'Elena Vasquez', 'Marcus Hill', 'Aisha Patel', 'Kiran Nags'],
)
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_standup, label='series a progress', defaults={'confidence': 0.96})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_standup, label='hiring updates',    defaults={'confidence': 0.93})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_standup, label='enterprise sales',  defaults={'confidence': 0.90})

m_bd = make_meeting(
    'BD & Partnerships Pipeline Review', 3, 'external', 'upload',
    'Tom walked through the full BD pipeline. '
    'EnterpriseX term sheet sent, response expected within 5 days. '
    'Two new LATAM prospects identified; intro decks needed.',
    ['Tom Bradley', 'Sarah Chen', 'Kiran Nags'],
)
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_bd, label='partnership pipeline', defaults={'confidence': 0.97})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_bd, label='enterprise sales',     defaults={'confidence': 0.94})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_bd, label='latam expansion',      defaults={'confidence': 0.85})

# Latest meeting — Gemini just ran, participants NOT confirmed, commitments pending_review
m_latest = make_meeting(
    'Leadership Standup — 19 May', 1, 'leadership', 'upload',
    'Quick round-the-table status check. '
    'Series A: investor call confirmed for next Tuesday, deck needs final polish. '
    'Hiring: last senior backend offer to go out this week. '
    'Tom flagged LATAM intro decks still outstanding.',
    ['Sarah Chen', 'James Okafor', 'Priya Nair', 'Tom Bradley', 'Marcus Hill', 'Kiran Nags'],
    confirmed=False,  # ← participant validation pending
)
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_latest, label='series a progress', defaults={'confidence': 0.95})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_latest, label='hiring pipeline',   defaults={'confidence': 0.91})
MeetingTopic.objects.get_or_create(organisation=org, meeting=m_latest, label='bd pipeline',       defaults={'confidence': 0.87})

print(f"\nMeetings created: {Meeting.objects.filter(organisation=org).count()}")


# ── Commitments ───────────────────────────────────────────────────────────────

def mkc(text, owner_name, meeting, status, priority, deadline,
        confidence, risk_score, tag_names=None, source='transcript',
        resolved_at=None, resolution_note=''):
    c, _ = Commitment.objects.get_or_create(
        organisation=org, normalised_text=text,
        defaults={
            'raw_text':       text,
            'owner':          people[owner_name],
            'meeting':        meeting,
            'status':         status,
            'priority':       priority,
            'deadline':       deadline,
            'confidence':     confidence,
            'risk_score':     risk_score,
            'source':         source,
            'resolved_at':    aware(resolved_at) if resolved_at else None,
            'resolution_note': resolution_note,
        },
    )
    if tag_names:
        c.tags.set([tags[t] for t in tag_names if t in tags])
    return c

print("\nCreating commitments...")

# ─────────────────────────────────────────────────────────────────────────────
# THREAD A — Series A fundraise
# Origin: board meeting (56d ago) → investor prep (28d ago) → weekly sync (7d ago)
# ─────────────────────────────────────────────────────────────────────────────

# A1 — Sarah sent the investor deck ✓ (done, closed cleanly)
ca1 = mkc(
    'Sarah Chen will send the updated Series A investor deck to the lead partner by 30 April.',
    'Sarah Chen', m_investor, 'done', 'high',
    days_ago(20), 0.97, 0.05, ['series a', 'board prep'],
    resolved_at=days_ago(21), resolution_note='Sent — lead partner confirmed receipt.',
)

# A2 — Marcus financial model overdue → at_risk (shows up in "Needs attention")
ca2 = mkc(
    'Marcus Hill will add a revenue sensitivity analysis to the financial model and share with Sarah.',
    'Marcus Hill', m_investor, 'at_risk', 'high',
    days_ago(4), 0.91, 0.88, ['series a', 'finance', 'data room'],
)

# A3 — Data room — active, on track (Marcus owns, from weekly sync)
ca3 = mkc(
    'Marcus Hill will complete the Series A data room and share access with the lead investor by 25 May.',
    'Marcus Hill', m_standup, 'active', 'high',
    days_from_now(5), 0.88, 0.48, ['series a', 'data room', 'finance'],
)

# A4 — Kiran investor update — done (from board meeting)
ca4 = mkc(
    'Kiran Nags will update the investor data room with Q1 financials and board deck by 15 April.',
    'Kiran Nags', m_board, 'done', 'high',
    days_ago(41), 0.95, 0.05, ['series a', 'board prep', 'finance'],
    resolved_at=days_ago(43), resolution_note='Uploaded Q1 pack to data room. Board confirmed.',
)

# ─────────────────────────────────────────────────────────────────────────────
# THREAD B — Engineering hiring
# Origin: Q2 kickoff (42d) → eng deep-dive (21d) → weekly sync (7d)
# ─────────────────────────────────────────────────────────────────────────────

# B1 — James published JDs ✓ (done, from Q2 kickoff)
cb1 = mkc(
    'James Okafor will publish job descriptions for 5 senior engineering roles on Lever by 20 April.',
    'James Okafor', m_q2kick, 'done', 'high',
    days_ago(22), 0.94, 0.05, ['hiring', 'engineering'],
    resolved_at=days_ago(24), resolution_note='All 5 JDs published. Applications open.',
)

# B2 — James senior interviews — ESCALATED + overdue (he's the problem)
cb2 = mkc(
    'James Okafor will complete first-round interviews for the 3 senior backend roles and share shortlist with Aisha.',
    'James Okafor', m_eng, 'escalated', 'high',
    days_ago(5), 0.89, 0.96, ['hiring', 'engineering'],
)

# B3 — Aisha offers — at_risk (from weekly sync)
cb3 = mkc(
    'Aisha Patel will send offer letters to the 2 approved engineering candidates by 20 May.',
    'Aisha Patel', m_standup, 'at_risk', 'high',
    days_from_now(1), 0.87, 0.81, ['hiring'],
)

# ─────────────────────────────────────────────────────────────────────────────
# THREAD C — Security & infrastructure
# Origin: engineering deep-dive (21d ago)
# ─────────────────────────────────────────────────────────────────────────────

# C1 — Security audit done ✓
cc1 = mkc(
    'Elena Vasquez will complete the production infrastructure security audit and share findings before go-live.',
    'Elena Vasquez', m_eng, 'done', 'high',
    days_ago(7), 0.93, 0.06, ['security', 'engineering'],
    resolved_at=days_ago(8), resolution_note='Audit complete. 2 low findings, 0 critical. Report shared.',
)

# C2 — DB migration — active, on track
cc2 = mkc(
    'Elena Vasquez will migrate the production database to eu-west-2 with zero-downtime cutover by 31 May.',
    'Elena Vasquez', m_eng, 'active', 'high',
    days_from_now(11), 0.91, 0.38, ['engineering', 'security'],
)

# ─────────────────────────────────────────────────────────────────────────────
# THREAD D — Product launch
# Origin: product review (14d) → weekly sync (7d)
# ─────────────────────────────────────────────────────────────────────────────

# D1 — Priya Q2 roadmap — done ✓
cd1 = mkc(
    'Priya Nair will finalise the Q2 product roadmap and circulate to board before the end of April.',
    'Priya Nair', m_product, 'done', 'high',
    days_ago(6), 0.96, 0.06, ['product', 'board prep'],
    resolved_at=days_ago(8), resolution_note='Roadmap circulated. Board acknowledged receipt.',
)

# D2 — Priya design partner interviews — active on track
cd2 = mkc(
    'Priya Nair will schedule and complete 5 design partner interviews before end of June.',
    'Priya Nair', m_product, 'active', 'medium',
    days_from_now(41), 0.90, 0.22, ['product', 'product launch'],
)

# D3 — Elena API rate limiting — at_risk (launch dependency)
cd3 = mkc(
    'Elena Vasquez will ship the new API rate limiting layer before the July product launch.',
    'Elena Vasquez', m_product, 'at_risk', 'high',
    days_from_now(6), 0.88, 0.77, ['engineering', 'product launch'],
)

# D4 — Kiran Q2 OKRs — done ✓ (from Q2 kickoff)
cd4 = mkc(
    'Kiran Nags will publish the Q2 OKRs to all teams and get sign-off from each team lead by 15 April.',
    'Kiran Nags', m_q2kick, 'done', 'medium',
    days_ago(27), 0.92, 0.05, ['okrs'],
    resolved_at=days_ago(29), resolution_note='OKRs published in Notion. All TLs confirmed.',
)

# ─────────────────────────────────────────────────────────────────────────────
# THREAD E — BD & partnerships
# Origin: Q2 kickoff (42d) → BD meeting (3d)
# ─────────────────────────────────────────────────────────────────────────────

# E1 — Tom enterprise pilots — ESCALATED + overdue (long overdue, he keeps slipping)
ce1 = mkc(
    'Tom Bradley will close 3 enterprise pilot agreements by end of Q2 — first pilot signed by 30 April.',
    'Tom Bradley', m_q2kick, 'escalated', 'high',
    days_ago(20), 0.86, 0.97, ['sales', 'partnerships'],
)

# E2 — Tom EnterpriseX term sheet — active (from BD meeting, recent)
ce2 = mkc(
    'Tom Bradley will send the finalised partnership term sheet to EnterpriseX by 22 May.',
    'Tom Bradley', m_bd, 'active', 'high',
    days_from_now(2), 0.92, 0.55, ['partnerships', 'legal'],
)

# E3 — Tom LATAM decks — active (from BD meeting)
ce3 = mkc(
    'Tom Bradley will prepare intro decks for the two LATAM prospects and share with Sarah for review.',
    'Tom Bradley', m_bd, 'active', 'medium',
    days_from_now(7), 0.85, 0.40, ['sales', 'partnerships'],
)

# ─────────────────────────────────────────────────────────────────────────────
# THREAD F — Operations
# ─────────────────────────────────────────────────────────────────────────────

# F1 — Marcus vendor contracts — ESCALATED (from weekly sync, renewal past due)
cf1 = mkc(
    'Marcus Hill will renegotiate and sign the 3 key SaaS vendor renewals before they lapse on 15 May.',
    'Marcus Hill', m_standup, 'escalated', 'high',
    days_ago(5), 0.90, 0.97, ['legal', 'finance'],
)

# F2 — Deferred: HR platform evaluation (no urgency, moved to Q3)
cf2 = mkc(
    'Marcus Hill will evaluate Rippling vs Workday and produce a recommendation for the board.',
    'Marcus Hill', m_q2kick, 'deferred', 'low',
    days_from_now(90), 0.74, 0.10, ['finance'],
)

# F3 — Cancelled: in-person product demo (replaced by a virtual one)
cf3 = mkc(
    'Tom Bradley will organise a Zoom product webinar for 50 prospects by end of April.',
    'Tom Bradley', m_q2kick, 'cancelled', 'low',
    days_ago(12), 0.69, 0.05, ['sales'],
)

# ─────────────────────────────────────────────────────────────────────────────
# LATEST MEETING — all pending_review (extraction just ran)
# Five items across the confidence spectrum to test bulk-confirm threshold
# ─────────────────────────────────────────────────────────────────────────────

cp1 = mkc(
    'Sarah Chen will send the final Series A deck to the lead investor before Tuesday\'s call.',
    'Sarah Chen', m_latest, 'pending_review', 'high',
    days_from_now(5), 0.96, 0.42, ['series a', 'board prep'],
)
cp2 = mkc(
    'James Okafor will send the final senior backend offer letter by end of this week.',
    'James Okafor', m_latest, 'pending_review', 'high',
    days_from_now(4), 0.91, 0.50, ['hiring', 'engineering'],
)
cp3 = mkc(
    'Priya Nair will book the first two design partner interview sessions by Friday.',
    'Priya Nair', m_latest, 'pending_review', 'medium',
    days_from_now(4), 0.82, 0.38, ['product', 'product launch'],
)
cp4 = mkc(
    'Tom Bradley will send the LATAM intro deck to Sarah for review before the weekend.',
    'Tom Bradley', m_latest, 'pending_review', 'medium',
    days_from_now(3), 0.75, 0.44, ['sales', 'partnerships'],
)
cp5 = mkc(
    'Marcus Hill will check whether the three vendor renewals have all been countersigned.',
    'Marcus Hill', m_latest, 'pending_review', 'low',
    days_from_now(7), 0.58, 0.32, ['legal', 'finance'],
)

print(f"  {Commitment.objects.filter(organisation=org).count()} commitments total")


# ── Commitment Events — full audit trail ──────────────────────────────────────
# For commitments that have a history, write events newest-first so the timeline
# reads correctly on the detail screen.

def add_event(commitment, event_type, actor_name, days_offset=0, hours_offset=0,
              old_val=None, new_val=None, note=''):
    evt = CommitmentEvent.objects.create(
        commitment=commitment,
        event_type=event_type,
        actor=people[actor_name],
        old_value=old_val,
        new_value=new_val,
        note=note,
    )
    CommitmentEvent.objects.filter(pk=evt.pk).update(
        occurred_at=t_ago(days=days_offset, hours=hours_offset)
    )

# ca1 — Sarah's investor deck (done): confirm → nudge → resolved
add_event(ca1, 'confirmed',    'Kiran Nags',  days_offset=27, note='High confidence — confirmed immediately.')
add_event(ca1, 'nudged',       'Kiran Nags',  days_offset=22, note='Reminder sent 2 days before deadline.')
add_event(ca1, 'resolved',     'Kiran Nags',  days_offset=21,
          new_val={'outcome': 'done'}, note='Sarah confirmed deck sent to lead partner.')

# ca2 — Marcus financial model (at_risk, overdue): confirm → field_edit (deadline extension) → nudge
add_event(ca2, 'confirmed',    'Kiran Nags',  days_offset=27, note='Confirmed from investor prep meeting.')
add_event(ca2, 'field_edited', 'Kiran Nags',  days_offset=14,
          old_val={'deadline': str(days_ago(18))},
          new_val={'deadline': str(days_ago(4))},
          note='Extended deadline at Marcus\'s request — revenue model complexity underestimated.')
add_event(ca2, 'nudged',       'Kiran Nags',  days_offset=6,  note='Sent Slack nudge 48h before revised deadline.')

# cb2 — James interviews (escalated, overdue): confirm → field_edit (owner clarified) → nudge → escalate × 2
add_event(cb2, 'confirmed',    'Kiran Nags',  days_offset=20, note='Confirmed from engineering deep-dive.')
add_event(cb2, 'field_edited', 'Kiran Nags',  days_offset=15,
          old_val={'owner': 'James Okafor', 'deadline': str(days_ago(14))},
          new_val={'owner': 'James Okafor', 'deadline': str(days_ago(5))},
          note='Deadline adjusted — initial pipeline took longer to build than expected.')
add_event(cb2, 'nudged',       'Kiran Nags',  days_offset=8,  note='Slack nudge sent — interviews still not started.')
add_event(cb2, 'escalated',    'Kiran Nags',  days_offset=6,  note='First escalation — 2 weeks overdue.')
add_event(cb2, 'nudged',       'Kiran Nags',  days_offset=3,  note='Second nudge — no response to first escalation.')
add_event(cb2, 'escalated',    'Kiran Nags',  days_offset=1,  note='Re-escalated to Sarah — blocking offer letters.')

# ce1 — Tom enterprise pilots (escalated, very overdue): confirm → nudge → edit (owner changed once) → escalate
add_event(ce1, 'confirmed',    'Kiran Nags',  days_offset=41, note='Confirmed from Q2 kickoff.')
add_event(ce1, 'nudged',       'Kiran Nags',  days_offset=28, note='Nudge sent — Q2 is a third done, no pilot signed.')
add_event(ce1, 'field_edited', 'Kiran Nags',  days_offset=22,
          old_val={'deadline': str(days_ago(35))},
          new_val={'deadline': str(days_ago(20))},
          note='Deadline brought forward after board pressure.')
add_event(ce1, 'nudged',       'Kiran Nags',  days_offset=15, note='Second Slack nudge sent.')
add_event(ce1, 'escalated',    'Kiran Nags',  days_offset=10, note='Escalated to Sarah — first pilot 3 weeks overdue.')
add_event(ce1, 'nudged',       'Kiran Nags',  days_offset=5,  note='Third nudge. Tom replied: "in negotiation".')

# cf1 — Marcus vendor contracts (escalated): confirm → nudge → escalate
add_event(cf1, 'confirmed',    'Kiran Nags',  days_offset=7,  note='Confirmed from weekly sync.')
add_event(cf1, 'nudged',       'Kiran Nags',  days_offset=5,  note='Renewal deadline in 3 days — Slack nudge sent.')
add_event(cf1, 'escalated',    'Kiran Nags',  days_offset=3,  note='Two contracts lapsed — escalated to Sarah.')

# ca4 — Kiran data room (done, then REOPENED — investor asked for more detail)
add_event(ca4, 'confirmed',    'Kiran Nags',  days_offset=55, note='Self-assigned from board meeting.')
add_event(ca4, 'resolved',     'Kiran Nags',  days_offset=43,
          new_val={'outcome': 'done'}, note='Q1 pack uploaded to data room.')
add_event(ca4, 'reopened',     'Kiran Nags',  days_offset=30,
          old_val={'status': 'done'},
          new_val={'status': 'active', 'deadline': str(days_ago(25))},
          note='Lead investor asked for deeper unit economics breakdown — reopened.')
add_event(ca4, 'field_edited', 'Kiran Nags',  days_offset=28,
          old_val={'normalised_text': 'Update investor data room with Q1 financials and board deck.'},
          new_val={'normalised_text': 'Update investor data room with Q1 financials, board deck, and unit economics breakdown.'},
          note='Expanded scope per investor request.')
add_event(ca4, 'resolved',     'Kiran Nags',  days_offset=25,
          new_val={'outcome': 'done'}, note='Unit economics section added. Investor confirmed satisfied.')

# cc1 — Security audit (done): confirm → resolved
add_event(cc1, 'confirmed',    'Kiran Nags',  days_offset=21, note='Confirmed from eng deep-dive.')
add_event(cc1, 'resolved',     'Kiran Nags',  days_offset=8,
          new_val={'outcome': 'done'}, note='Audit report shared. No critical findings.')

# Simple confirmed events for clean items
for c, n, d in [
    (cb1, 'Kiran Nags', 41), (cd1, 'Kiran Nags', 14),
    (cd4, 'Kiran Nags', 41), (cf2, 'Kiran Nags', 41),
]:
    add_event(c, 'confirmed', n, days_offset=d)

for c, n, d in [
    (cb1, 'Kiran Nags', 24), (cd1, 'Kiran Nags',  8),
    (cd4, 'Kiran Nags', 29),
]:
    add_event(c, 'resolved', n, days_offset=d, new_val={'outcome': 'done'})

add_event(cf3, 'confirmed', 'Kiran Nags', days_offset=41)
add_event(cf3, 'rejected',  'Kiran Nags', days_offset=12,
          note='Cancelled — replaced by in-person event in London.')

print(f"  {CommitmentEvent.objects.filter(commitment__organisation=org).count()} commitment events")


# ── Escalation Events ─────────────────────────────────────────────────────────

def add_escalation(commitment, by_name, to_name, method, outcome, n_days_ago, message):
    esc = EscalationEvent.objects.create(
        commitment=commitment,
        escalated_by=people[by_name],
        escalated_to=people[to_name],
        method=method,
        message_sent=message,
        outcome=outcome,
    )
    EscalationEvent.objects.filter(pk=esc.pk).update(occurred_at=t_ago(days=n_days_ago))

# cb2 — James interviews (two escalations, second still open)
add_escalation(
    cb2, 'Kiran Nags', 'James Okafor', 'slack', 'responded', 6,
    'James — the shortlist for the backend roles was due last week. Can we get an update by EOD?',
)
add_escalation(
    cb2, 'Kiran Nags', 'Sarah Chen', 'manual', 'pending', 1,
    'Sarah — escalating. James\'s hiring shortlist is 2 weeks late and is blocking Aisha\'s offer letters.',
)

# ce1 — Tom pilots (one escalation, still pending)
add_escalation(
    ce1, 'Kiran Nags', 'Tom Bradley', 'slack', 'responded', 10,
    'Tom — the first enterprise pilot was meant to be signed by end of April. Where are we?',
)
add_escalation(
    ce1, 'Kiran Nags', 'Sarah Chen', 'manual', 'pending', 5,
    'Sarah — Tom\'s enterprise pilot target is 3 weeks overdue. Flagging for your Monday call with him.',
)

# cf1 — Marcus vendor contracts
add_escalation(
    cf1, 'Kiran Nags', 'Marcus Hill', 'slack', 'pending', 3,
    'Marcus — 2 of the 3 vendor contracts have now lapsed. Need urgent action on this.',
)

print(f"  {EscalationEvent.objects.filter(commitment__organisation=org).count()} escalation events")


# ── Extraction Feedback ───────────────────────────────────────────────────────
# Logged when CoS confirmed or rejected a commitment from the review queue.

feedback_data = [
    (ca1, 'confirmed', ''),
    (ca4, 'confirmed', ''),
    (cb1, 'confirmed', ''),
    (cb2, 'confirmed', 'Confirmed. Deadline shifted after first conversation with James.'),
    (cc1, 'confirmed', ''),
    (cd1, 'confirmed', ''),
    (cd4, 'confirmed', ''),
    (ce1, 'confirmed', 'Confirmed. Tom acknowledged commitment on the call.'),
    (cf3, 'rejected',  'Not a real commitment — was a suggestion. Tom clarified it was tentative.'),
    (ca2, 'confirmed', ''),
    (ca2, 'wrong_date', 'Original deadline was 7 May. Corrected to 16 May during review.'),
]

for commitment, ftype, note in feedback_data:
    ExtractionFeedback.objects.get_or_create(
        commitment=commitment, feedback_type=ftype,
        defaults={'organisation': org, 'note': note, 'given_by': cos, 'from_import': False},
    )

print(f"  {ExtractionFeedback.objects.filter(organisation=org).count()} feedback records")


# ── Nudge Logs ────────────────────────────────────────────────────────────────

def add_nudge(commitment, n_days_ago):
    nudge = NudgeLog.objects.create(commitment=commitment, channel='slack')
    NudgeLog.objects.filter(pk=nudge.pk).update(nudged_at=t_ago(days=n_days_ago))

add_nudge(ca2, 6)   # Marcus financial model
add_nudge(cb2, 8)   # James interviews (first nudge)
add_nudge(cb2, 3)   # James interviews (second nudge)
add_nudge(ce1, 28)  # Tom pilots (first)
add_nudge(ce1, 15)  # Tom pilots (second)
add_nudge(ce1, 5)   # Tom pilots (third)
add_nudge(cf1, 5)   # Marcus vendor contracts
add_nudge(cb3, 0)   # Aisha offer letters — sent today

print(f"  {NudgeLog.objects.filter(commitment__organisation=org).count()} nudge log entries")


# ── Final summary ─────────────────────────────────────────────────────────────

from django.db.models import Count
status_counts = (
    Commitment.objects.filter(organisation=org)
    .values('status').annotate(n=Count('id')).order_by('status')
)

print("\n=== Seed complete ===")
print(f"Org:         {org.name}")
print(f"People:      {Person.objects.filter(organisation=org).count()}")
print(f"Meetings:    {Meeting.objects.filter(organisation=org).count()}")
print(f"Topics:      {MeetingTopic.objects.filter(organisation=org).count()}")
print(f"Tags:        {CommitmentTag.objects.filter(organisation=org).count()}")
print(f"Commitments: {Commitment.objects.filter(organisation=org).count()}")
print("Status breakdown:")
for row in status_counts:
    print(f"  {row['status']:15s}  {row['n']}")
print(f"Events:      {CommitmentEvent.objects.filter(commitment__organisation=org).count()}")
print(f"Escalations: {EscalationEvent.objects.filter(commitment__organisation=org).count()}")
print(f"Feedback:    {ExtractionFeedback.objects.filter(organisation=org).count()}")
print(f"Nudges:      {NudgeLog.objects.filter(commitment__organisation=org).count()}")
print("""
Narrative threads:
  A — Series A:        4 commitments across board → investor prep → weekly sync
  B — Engineering hiring: 3 commitments across Q2 kickoff → eng deep-dive → standup
  C — Security/infra:  2 commitments from eng deep-dive
  D — Product launch:  4 commitments from product review → Q2 kickoff
  E — BD pipeline:     3 commitments from Q2 kickoff → BD meeting
  F — Operations:      3 commitments (1 escalated, 1 deferred, 1 cancelled)
  Latest meeting:      5 pending_review + unconfirmed participants

Interesting data points:
  • ca4 (Kiran data room) was resolved DONE then REOPENED — shows reopen flow
  • cb2 (James hiring) has 6 events + 2 escalations — rich audit trail
  • ce1 (Tom pilots) has 6 events + 2 escalations — shows pattern of slippage
  • Tom Bradley: 52% delivery rate, 3 overdue/escalated commitments
  • Latest meeting has confirmed=False on all participants — participant validation pending
  • 5 pending_review commitments span the 0.58–0.96 confidence range
""")
