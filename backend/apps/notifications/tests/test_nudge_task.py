"""Tests for send_deadline_nudges Celery task (Week 6)."""
import pytest
from datetime import date, timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organisation, User, Person
from apps.commitments.models import Commitment
from apps.meetings.models import Meeting
from apps.notifications.models import NudgeLog
from apps.notifications.tasks import send_deadline_nudges


@pytest.fixture
def org(db):
    return Organisation.objects.create(name='Test Org', slug='test-org')


@pytest.fixture
def meeting(org):
    return Meeting.objects.create(
        organisation=org, title='Test Meeting', occurred_at=timezone.now(),
    )


@pytest.fixture
def slack_owner(org):
    return Person.objects.create(
        organisation=org, name='Alice', slack_user_id='U123456',
    )


@pytest.fixture
def no_slack_owner(org):
    return Person.objects.create(organisation=org, name='Bob', slack_user_id='')


def make_commitment(org, meeting, owner=None, deadline=None, status=Commitment.Status.ACTIVE):
    return Commitment.objects.create(
        organisation=org, meeting=meeting,
        raw_text='x', normalised_text='x', confidence=0.9,
        owner=owner, deadline=deadline, status=status,
    )


@pytest.mark.django_db
class TestSendDeadlineNudges:
    def test_nudges_owner_with_slack_id(self, org, meeting, slack_owner):
        tomorrow = date.today() + timedelta(days=1)
        make_commitment(org, meeting, owner=slack_owner, deadline=tomorrow)

        with patch('apps.notifications.tasks.send_nudge_dm', return_value='DM123') as mock_dm:
            result = send_deadline_nudges.apply(throw=True).get()

        mock_dm.assert_called_once()
        assert result['sent'] == 1

    def test_no_nudge_without_slack_id(self, org, meeting, no_slack_owner):
        tomorrow = date.today() + timedelta(days=1)
        make_commitment(org, meeting, owner=no_slack_owner, deadline=tomorrow)

        with patch('apps.notifications.tasks.send_nudge_dm') as mock_dm:
            result = send_deadline_nudges.apply(throw=True).get()

        mock_dm.assert_not_called()
        assert result['sent'] == 0

    def test_no_nudge_past_deadline(self, org, meeting, slack_owner):
        yesterday = date.today() - timedelta(days=1)
        make_commitment(org, meeting, owner=slack_owner, deadline=yesterday)

        with patch('apps.notifications.tasks.send_nudge_dm') as mock_dm:
            result = send_deadline_nudges.apply(throw=True).get()

        mock_dm.assert_not_called()
        assert result['sent'] == 0

    def test_no_nudge_far_future_deadline(self, org, meeting, slack_owner):
        far = date.today() + timedelta(days=10)
        make_commitment(org, meeting, owner=slack_owner, deadline=far)

        with patch('apps.notifications.tasks.send_nudge_dm') as mock_dm:
            result = send_deadline_nudges.apply(throw=True).get()

        mock_dm.assert_not_called()
        assert result['sent'] == 0

    def test_no_double_nudge_within_cooldown(self, org, meeting, slack_owner):
        tomorrow = date.today() + timedelta(days=1)
        c = make_commitment(org, meeting, owner=slack_owner, deadline=tomorrow)
        NudgeLog.objects.create(commitment=c, nudged_at=timezone.now(), channel='DM123')

        with patch('apps.notifications.tasks.send_nudge_dm') as mock_dm:
            result = send_deadline_nudges.apply(throw=True).get()

        mock_dm.assert_not_called()
        assert result['sent'] == 0

    def test_nudge_log_created(self, org, meeting, slack_owner):
        tomorrow = date.today() + timedelta(days=1)
        c = make_commitment(org, meeting, owner=slack_owner, deadline=tomorrow)

        with patch('apps.notifications.tasks.send_nudge_dm', return_value='DM123'):
            send_deadline_nudges.apply(throw=True)

        assert NudgeLog.objects.filter(commitment=c).count() == 1

    def test_delivered_commitment_not_nudged(self, org, meeting, slack_owner):
        tomorrow = date.today() + timedelta(days=1)
        make_commitment(
            org, meeting, owner=slack_owner, deadline=tomorrow,
            status=Commitment.Status.DELIVERED,
        )

        with patch('apps.notifications.tasks.send_nudge_dm') as mock_dm:
            result = send_deadline_nudges.apply(throw=True).get()

        mock_dm.assert_not_called()
        assert result['sent'] == 0

    def test_empty_org_returns_zero(self, org):
        with patch('apps.notifications.tasks.send_nudge_dm') as mock_dm:
            result = send_deadline_nudges.apply(throw=True).get()

        mock_dm.assert_not_called()
        assert result == {'sent': 0}
