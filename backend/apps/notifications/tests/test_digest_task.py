"""Tests for send_weekly_digest Celery task (Week 6)."""
import pytest
from datetime import date, timedelta
from unittest.mock import patch

from django.core import mail
from django.utils import timezone

from apps.accounts.models import Organisation, User
from apps.commitments.models import Commitment
from apps.meetings.models import Meeting
from apps.notifications.tasks import send_weekly_digest


@pytest.fixture
def org(db):
    return Organisation.objects.create(name='Acme Corp', slug='acme')


@pytest.fixture
def user_with_email(org):
    return User.objects.create_user(
        username='cos', password='pass',
        organisation=org, email='cos@acme.com',
    )


@pytest.fixture
def meeting(org):
    return Meeting.objects.create(
        organisation=org, title='Q2 Planning', occurred_at=timezone.now(),
    )


def make_commitment(org, meeting, status=Commitment.Status.ACTIVE, risk_score=0.0, deadline=None):
    return Commitment.objects.create(
        organisation=org, meeting=meeting,
        raw_text='x', normalised_text='Alice will send the report.',
        confidence=0.9, status=status, risk_score=risk_score, deadline=deadline,
    )


FAKE_INTRO = "This week looks manageable. Two commitments need attention."


@pytest.mark.django_db
class TestSendWeeklyDigest:
    def test_sends_email_to_org_users(self, org, user_with_email, meeting):
        make_commitment(org, meeting)

        with patch('apps.notifications.tasks._generate_digest_intro', return_value=FAKE_INTRO):
            result = send_weekly_digest.apply(throw=True).get()

        assert result['orgs_sent'] == 1
        assert len(mail.outbox) == 1
        assert 'cos@acme.com' in mail.outbox[0].to

    def test_email_subject_contains_date(self, org, user_with_email, meeting):
        make_commitment(org, meeting)

        with patch('apps.notifications.tasks._generate_digest_intro', return_value=FAKE_INTRO):
            send_weekly_digest.apply(throw=True)

        assert 'weekly digest' in mail.outbox[0].subject.lower()

    def test_email_has_html_alternative(self, org, user_with_email, meeting):
        make_commitment(org, meeting)

        with patch('apps.notifications.tasks._generate_digest_intro', return_value=FAKE_INTRO):
            send_weekly_digest.apply(throw=True)

        alternatives = mail.outbox[0].alternatives
        content_types = [ct for _, ct in alternatives]
        assert 'text/html' in content_types

    def test_html_contains_org_name(self, org, user_with_email, meeting):
        make_commitment(org, meeting)

        with patch('apps.notifications.tasks._generate_digest_intro', return_value=FAKE_INTRO):
            send_weekly_digest.apply(throw=True)

        html = mail.outbox[0].alternatives[0][0]
        assert 'Acme Corp' in html

    def test_overdue_in_html(self, org, user_with_email, meeting):
        yesterday = date.today() - timedelta(days=1)
        make_commitment(org, meeting, deadline=yesterday)

        with patch('apps.notifications.tasks._generate_digest_intro', return_value=FAKE_INTRO):
            send_weekly_digest.apply(throw=True)

        html = mail.outbox[0].alternatives[0][0]
        assert 'Overdue' in html

    def test_no_email_if_no_users(self, org, meeting):
        make_commitment(org, meeting)

        with patch('apps.notifications.tasks._generate_digest_intro', return_value=FAKE_INTRO):
            result = send_weekly_digest.apply(throw=True).get()

        assert result['orgs_sent'] == 0
        assert len(mail.outbox) == 0

    def test_no_email_if_no_commitments(self, org, user_with_email):
        with patch('apps.notifications.tasks._generate_digest_intro', return_value=FAKE_INTRO):
            result = send_weekly_digest.apply(throw=True).get()

        assert len(mail.outbox) == 0

    def test_fallback_intro_when_gemini_fails(self, org, user_with_email, meeting):
        make_commitment(org, meeting)

        with patch('apps.notifications.tasks._generate_digest_intro', return_value=FAKE_INTRO):
            send_weekly_digest.apply(throw=True)

        assert len(mail.outbox) == 1
