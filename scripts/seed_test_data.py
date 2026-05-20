"""
Frontend test seed — run via:
  python manage.py shell < scripts/seed_test_data.py

Covers every screen in the v0.3 prototype:
  • Dashboard — all 4 stat cards, both filter axes, priority chips
  • Extraction review — pending items spanning the confidence range
  • Commitment detail — escalation history, feedback, tags
  • People analytics — varied delivery rates and roles
  • Meetings list — 7 meetings across 3 months

Pass CLEAR=1 to wipe existing seed data first:
  CLEAR=1 python manage.py shell < scripts/seed_test_data.py
"""
import os
from datetime import date, datetime, timedelta
from django.utils import timezone
from apps.accounts.models import User, Organisation, Person
from apps.meetings.models import Meeting, MeetingParticipant
from apps.commitments.models import (
    Commitment, CommitmentTag, EscalationEvent, ExtractionFeedback,
)

today = date.today()
now   = timezone.now()

CLEAR = os.environ.get('CLEAR', '').strip() == '1'

# ── Helpers ───────────────────────────────────────────────────────────────────

def aware(d):
    """Convert a date to a timezone-aware midnight datetime."""
    return timezone.make_aware(datetime.combine(d, datetime.min.time()))


def days_ago(n):
    return today - timedelta(days=n)


def days_from_now(n):
    return today + timedelta(days=n)


# ── Org ───────────────────────────────────────────────────────────────────────

org, _ = Organisation.objects.get_or_create(
    slug='twocents',
    defaults={'name': 'TwoCents Capital', 'plan': 'team'},
)
print(f"Org: {org.name}")

# ── User ──────────────────────────────────────────────────────────────────────

user = User.objects.get(email='kanags@gmail.com')
user.organisation = org
user.is_org_admin  = True
user.save()
print(f"User: {user.email}")

# ── Optional clear ────────────────────────────────────────────────────────────

if CLEAR:
    EscalationEvent.objects.filter(commitment__organisation=org).delete()
    ExtractionFeedback.objects.filter(organisation=org).delete()
    Commitment.objects.filter(organisation=org).delete()
    MeetingParticipant.objects.filter(meeting__organisation=org).delete()
    Meeting.objects.filter(organisation=org).delete()
    CommitmentTag.objects.filter(organisation=org).delete()
    Person.objects.filter(organisation=org).exclude(user=user).delete()
    print("Cleared existing seed data.")

# ── People (6 + CoS) ─────────────────────────────────────────────────────────
# Roles visible on People analytics page.
# delivery_rate drives risk scores and the colour-coded delivery bars.

people_data = [
    # (name, email, role, delivery_rate, avg_days_late, total_commitments, meeting_count)
    ('Sarah Chen',    'sarah@twocents.ai',  'Chief of Staff',         0.92, 0.5,  24, 12),
    ('James Okafor',  'james@twocents.ai',  'VP Engineering',         0.61, 4.2,  31,  9),
    ('Priya Nair',    'priya@twocents.ai',  'Head of Product',        0.80, 1.8,  18,  8),
    ('Tom Bradley',   'tom@twocents.ai',    'VP Business Development', 0.55, 6.1,  22,  7),
    ('Elena Vasquez', 'elena@twocents.ai',  'Head of Engineering',    0.88, 0.9,  15,  6),
    ('Marcus Hill',   'marcus@twocents.ai', 'CFO',                    0.73, 2.4,  11,  5),
]

people = {}
for name, email, role, dr, adl, tc, mc in people_data:
    p, created = Person.objects.get_or_create(
        organisation=org,
        email=email,
        defaults={
            'name': name,
            'role': role,
            'delivery_rate': dr,
            'avg_days_late': adl,
            'total_commitments': tc,
            'meeting_count': mc,
        },
    )
    if not created:
        p.name = name; p.role = role; p.delivery_rate = dr
        p.avg_days_late = adl; p.total_commitments = tc; p.meeting_count = mc
        p.save()
    people[name] = p
    print(f"  Person: {name} ({role}) — delivery {int(dr*100)}%")

# CoS / logged-in user
cos, _ = Person.objects.get_or_create(
    organisation=org,
    email='kanags@gmail.com',
    defaults={
        'name': 'Kiran Nags',
        'role': 'Chief of Staff',
        'user': user,
        'delivery_rate': 0.95,
        'total_commitments': 8,
        'meeting_count': 15,
    },
)
people['Kiran Nags'] = cos

# ── Meetings (7) ──────────────────────────────────────────────────────────────

meetings_data = [
    # (title, days_ago, meeting_type, platform, participants_names)
    (
        'Board Meeting — Q1 Review',
        42, 'board', 'upload',
        ['Sarah Chen', 'James Okafor', 'Marcus Hill', 'Kiran Nags'],
    ),
    (
        'Q2 Leadership Planning',
        21, 'leadership', 'upload',
        ['Sarah Chen', 'James Okafor', 'Priya Nair', 'Tom Bradley', 'Elena Vasquez', 'Marcus Hill', 'Kiran Nags'],
    ),
    (
        'Investor Update Prep — Series A',
        14, 'one_on_one', 'upload',
        ['Sarah Chen', 'Marcus Hill', 'Kiran Nags'],
    ),
    (
        'Product Roadmap Review — Q2',
        7, 'team', 'upload',
        ['Priya Nair', 'James Okafor', 'Elena Vasquez', 'Kiran Nags'],
    ),
    (
        'Engineering Architecture Sync',
        5, 'project', 'upload',
        ['James Okafor', 'Elena Vasquez', 'Kiran Nags'],
    ),
    (
        'BD Pipeline Review',
        3, 'external', 'upload',
        ['Tom Bradley', 'Kiran Nags'],
    ),
    (
        'Weekly Leadership Standup',
        1, 'team', 'upload',
        ['Sarah Chen', 'James Okafor', 'Priya Nair', 'Tom Bradley', 'Elena Vasquez', 'Marcus Hill', 'Kiran Nags'],
    ),
]

meetings = []
for title, n_ago, mtype, platform, participant_names in meetings_data:
    m, _ = Meeting.objects.get_or_create(
        organisation=org,
        title=title,
        defaults={
            'occurred_at':       aware(days_ago(n_ago)),
            'meeting_type':      mtype,
            'platform':          platform,
            'processing_status': 'complete',
            'processed_at':      aware(days_ago(n_ago)),
            'summary':           f'Extracted commitments from {title}.',
        },
    )
    for pname in participant_names:
        if pname in people:
            MeetingParticipant.objects.get_or_create(meeting=m, person=people[pname])
    meetings.append(m)
    print(f"  Meeting: {title}")

# Shorthand
m_board, m_leadership, m_investor, m_product, m_eng, m_bd, m_standup = meetings

# ── Tags ──────────────────────────────────────────────────────────────────────

tag_labels = [
    'fundraising', 'board', 'hiring', 'engineering', 'product',
    'research', 'legal', 'partnerships', 'security', 'analytics',
    'marketing', 'strategy', 'onboarding', 'sales', 'finance',
]

tags = {}
for label in tag_labels:
    t, _ = CommitmentTag.objects.get_or_create(organisation=org, label=label)
    tags[label] = t


def make_commitment(
    text, owner_name, meeting, status, priority,
    deadline, confidence, risk_score,
    tag_names=None, source='transcript',
):
    c, created = Commitment.objects.get_or_create(
        organisation=org,
        normalised_text=text,
        defaults={
            'raw_text':     text,
            'owner':        people[owner_name],
            'meeting':      meeting,
            'status':       status,
            'priority':     priority,
            'deadline':     deadline,
            'confidence':   confidence,
            'risk_score':   risk_score,
            'source':       source,
        },
    )
    if created and tag_names:
        c.tags.set([tags[t] for t in tag_names if t in tags])
    return c, created


# ── Commitments ───────────────────────────────────────────────────────────────
# Distribution across statuses:
#   overdue (active/at_risk + past deadline): 4
#   at_risk (current):                        3
#   escalated:                                2
#   active / on-track:                        6
#   done:                                     4
#   deferred:                                 2
#   cancelled:                                1
#   pending_review:                           5  ← extraction review screen

print("\nCreating commitments...")

# ── OVERDUE — active/at_risk with past deadline ───────────────────────────────

c1, _ = make_commitment(
    'Send revised Series A investor deck to lead partner',
    'Sarah Chen', m_investor, 'at_risk', 'high',
    days_ago(3), 0.95, 0.93, ['fundraising', 'board'],
)
c2, _ = make_commitment(
    'Complete Q2 engineering hiring plan and share with all team leads',
    'James Okafor', m_leadership, 'at_risk', 'high',
    days_ago(5), 0.88, 0.91, ['hiring', 'engineering'],
)
c3, _ = make_commitment(
    'Draft partnership agreement with TechCorp and send for legal review',
    'Tom Bradley', m_bd, 'active', 'high',
    days_ago(10), 0.87, 0.96, ['legal', 'partnerships'],
)
c4, _ = make_commitment(
    'Migrate remaining customers to new billing system',
    'Elena Vasquez', m_leadership, 'active', 'high',
    days_ago(1), 0.92, 0.85, ['engineering', 'onboarding'],
)

# ── ESCALATED ─────────────────────────────────────────────────────────────────

c5, _ = make_commitment(
    'Complete security audit of production infrastructure before go-live',
    'Elena Vasquez', m_eng, 'escalated', 'high',
    days_from_now(2), 0.90, 0.94, ['security', 'engineering'],
)
c6, _ = make_commitment(
    'Renegotiate SaaS vendor contracts — renewal deadline approaching',
    'Marcus Hill', m_leadership, 'escalated', 'high',
    days_ago(2), 0.88, 0.97, ['legal', 'finance'],
)

# ── AT RISK (not yet overdue) ─────────────────────────────────────────────────

c7, _ = make_commitment(
    'Finalise board presentation deck for next month governance review',
    'Sarah Chen', m_board, 'at_risk', 'high',
    days_from_now(4), 0.89, 0.80, ['board', 'fundraising'],
)
c8, _ = make_commitment(
    'Complete financial model update for Series A data room',
    'Marcus Hill', m_investor, 'at_risk', 'medium',
    days_from_now(3), 0.85, 0.74, ['fundraising', 'finance'],
)
c9, _ = make_commitment(
    'Review and approve engineering architecture proposal for new infra',
    'James Okafor', m_eng, 'at_risk', 'medium',
    days_from_now(2), 0.83, 0.78, ['engineering'],
)

# ── ACTIVE / ON-TRACK ─────────────────────────────────────────────────────────

c10, _ = make_commitment(
    'Schedule user research sessions with 5 design partner companies',
    'Priya Nair', m_product, 'active', 'medium',
    days_from_now(7), 0.91, 0.45, ['product', 'research'],
)
c11, _ = make_commitment(
    'Implement new user onboarding flow based on design partner feedback',
    'Elena Vasquez', m_product, 'active', 'medium',
    days_from_now(14), 0.93, 0.30, ['product', 'onboarding'],
)
c12, _ = make_commitment(
    'Follow up with 3 enterprise leads from last conference',
    'Tom Bradley', m_standup, 'active', 'medium',
    days_from_now(5), 0.82, 0.40, ['sales'],
)
c13, _ = make_commitment(
    'Update pricing page copy and set up A/B test',
    'Priya Nair', m_product, 'active', 'low',
    days_from_now(21), 0.85, 0.20, ['product', 'marketing'],
)
c14, _ = make_commitment(
    'Finalise Q3 OKRs and get sign-off from all team leads',
    'Kiran Nags', m_leadership, 'active', 'high',
    days_from_now(7), 0.78, 0.55, ['strategy'],
)
c15, _ = make_commitment(
    'Set up weekly executive metrics dashboard and share access with leadership',
    'James Okafor', m_standup, 'active', 'medium',
    days_from_now(10), 0.80, 0.38, ['analytics'],
)

# ── DONE ──────────────────────────────────────────────────────────────────────

c16, _ = make_commitment(
    'Send weekly digest email to all investors covering Q1 highlights',
    'Kiran Nags', m_standup, 'done', 'medium',
    days_ago(1), 0.97, 0.05, ['fundraising'],
)
c17, _ = make_commitment(
    'Complete Q1 board pack and send to all board members 48h before meeting',
    'Sarah Chen', m_board, 'done', 'high',
    days_ago(7), 0.96, 0.08, ['board'],
)
c18, _ = make_commitment(
    'Publish engineering hiring JDs on Lever for senior backend roles',
    'James Okafor', m_leadership, 'done', 'medium',
    days_ago(14), 0.91, 0.05, ['hiring', 'engineering'],
)
c19, _ = make_commitment(
    'Audit all AWS IAM roles and remove stale permissions',
    'Elena Vasquez', m_eng, 'done', 'high',
    days_ago(5), 0.94, 0.07, ['security', 'engineering'],
)

# ── DEFERRED ──────────────────────────────────────────────────────────────────

c20, _ = make_commitment(
    'Explore acquisition opportunities in the HR-tech space',
    'Marcus Hill', m_board, 'deferred', 'low',
    days_from_now(90), 0.72, 0.10, ['strategy', 'finance'],
)
c21, _ = make_commitment(
    'Evaluate dedicated customer success platform (Gainsight vs Totango)',
    'Priya Nair', m_product, 'deferred', 'low',
    days_from_now(60), 0.75, 0.12, ['product'],
)

# ── CANCELLED ─────────────────────────────────────────────────────────────────

c22, _ = make_commitment(
    'Set up Zoom Webinar for external product demo — replaced by in-person event',
    'Tom Bradley', m_bd, 'cancelled', 'low',
    days_ago(3), 0.68, 0.05, ['sales'],
)

# ── PENDING REVIEW — extraction review screen ──────────────────────────────────
# Mix of confidence levels to test batch-confirm threshold logic

c23, _ = make_commitment(
    'Share updated competitive analysis with the full leadership team',
    'Sarah Chen', m_standup, 'pending_review', 'medium',
    days_from_now(10), 0.91, 0.40, ['strategy'],
)
c24, _ = make_commitment(
    'Prepare short-list of Series B advisors and share with board',
    'Marcus Hill', m_standup, 'pending_review', 'high',
    days_from_now(14), 0.87, 0.45, ['fundraising', 'board'],
)
c25, _ = make_commitment(
    'Draft v2 of the sales playbook incorporating lessons from last quarter',
    'Tom Bradley', m_standup, 'pending_review', 'medium',
    days_from_now(21), 0.76, 0.35, ['sales'],
)
c26, _ = make_commitment(
    'Review open legal queries with outside counsel',
    'Marcus Hill', m_standup, 'pending_review', 'high',
    days_from_now(7), 0.62, 0.50, ['legal'],
)
c27, _ = make_commitment(
    'Check with ops team whether the office lease renewal has been filed',
    'Kiran Nags', m_standup, 'pending_review', 'low',
    days_from_now(30), 0.54, 0.25, ['finance'],
)

print(f"  {Commitment.objects.filter(organisation=org).count()} commitments total")

# ── Escalation history — commitment detail timeline ───────────────────────────

escalation_configs = [
    # (commitment, escalated_by, escalated_to, method, outcome, days_ago_n, message)
    (
        c3, 'Kiran Nags', 'Tom Bradley', 'slack', 'pending',
        2, 'Hi Tom — the TechCorp partnership agreement was due last week. Any blockers?',
    ),
    (
        c3, 'Kiran Nags', 'Tom Bradley', 'slack', 'responded',
        1, 'Following up again — this is blocking the legal review timeline.',
    ),
    (
        c6, 'Kiran Nags', 'Marcus Hill', 'slack', 'pending',
        3, 'Marcus — vendor renewal deadline is tomorrow. Can you confirm status?',
    ),
    (
        c5, 'Kiran Nags', 'Elena Vasquez', 'manual', 'escalated',
        1, 'Escalating security audit to leadership — go-live is at risk.',
    ),
    (
        c2, 'Kiran Nags', 'James Okafor', 'slack', 'responded',
        4, 'James — Q2 hiring plan was due last week. Can we sync tomorrow?',
    ),
]

for commitment, by_name, to_name, method, outcome, n_ago, message in escalation_configs:
    EscalationEvent.objects.get_or_create(
        commitment=commitment,
        method=method,
        message_sent=message,
        defaults={
            'escalated_by': people[by_name],
            'escalated_to': people[to_name],
            'outcome': outcome,
            'occurred_at': now - timedelta(days=n_ago),
        },
    )

print(f"  {EscalationEvent.objects.filter(commitment__organisation=org).count()} escalation events")

# ── Extraction feedback — audit trail ──────────────────────────────────────────

feedback_configs = [
    # (commitment, feedback_type, note)
    (c16, 'confirmed', ''),
    (c17, 'confirmed', ''),
    (c18, 'confirmed', ''),
    (c19, 'confirmed', ''),
    (c1,  'confirmed', ''),
    (c2,  'confirmed', 'Confirmed but owner clarified timeline — updated deadline.'),
    (c3,  'confirmed', ''),
    (c4,  'confirmed', ''),
    (c5,  'confirmed', ''),
    (c10, 'confirmed', ''),
    (c22, 'rejected',  'Not a real commitment — was a suggestion, not an action item.'),
]

for commitment, ftype, note in feedback_configs:
    ExtractionFeedback.objects.get_or_create(
        commitment=commitment,
        feedback_type=ftype,
        defaults={
            'organisation': org,
            'note': note,
            'given_by': cos,
            'from_import': False,
        },
    )

print(f"  {ExtractionFeedback.objects.filter(organisation=org).count()} feedback records")

# ── Summary ───────────────────────────────────────────────────────────────────

from django.db.models import Count
status_counts = (
    Commitment.objects
    .filter(organisation=org)
    .values('status')
    .annotate(n=Count('id'))
    .order_by('status')
)

print("\n=== Seed complete ===")
print(f"Org:         {org.name}")
print(f"People:      {Person.objects.filter(organisation=org).count()}")
print(f"Meetings:    {Meeting.objects.filter(organisation=org).count()}")
print(f"Commitments: {Commitment.objects.filter(organisation=org).count()}")
print("Status breakdown:")
for row in status_counts:
    print(f"  {row['status']:15s}  {row['n']}")
print(f"\nTags: {', '.join(tag_labels)}")
print("Ready for frontend testing.")
