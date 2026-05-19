"""Action endpoint tests for Week 4: confirm, reject, escalate, resolve."""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organisation, User
from apps.commitments.models import Commitment, EscalationEvent, ExtractionFeedback
from apps.meetings.models import Meeting


@pytest.fixture
def org(db):
    return Organisation.objects.create(name='Test Org', slug='test-org')


@pytest.fixture
def user(org):
    return User.objects.create_user(username='cos', password='pass', organisation=org)


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def meeting(org):
    return Meeting.objects.create(
        organisation=org, title='Test Meeting', occurred_at=timezone.now(),
    )


@pytest.fixture
def pending(org, meeting):
    return Commitment.objects.create(
        organisation=org, meeting=meeting,
        raw_text='Alice will send the report.',
        normalised_text='Alice will send the report.',
        confidence=0.9,
        status=Commitment.Status.PENDING_REVIEW,
    )


@pytest.fixture
def active(org, meeting):
    return Commitment.objects.create(
        organisation=org, meeting=meeting,
        raw_text='Bob will update the deck.',
        normalised_text='Bob will update the deck.',
        confidence=0.9,
        status=Commitment.Status.ACTIVE,
    )


@pytest.fixture
def delivered(org, meeting):
    return Commitment.objects.create(
        organisation=org, meeting=meeting,
        raw_text='Done.', normalised_text='Done.',
        confidence=0.9,
        status=Commitment.Status.DELIVERED,
    )


# ── confirm ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestConfirm:
    def test_transitions_to_active(self, client, pending):
        resp = client.post(f'/api/v1/commitments/{pending.id}/confirm/')
        assert resp.status_code == 200
        assert resp.data['status'] == 'active'

    def test_sets_reviewed_at(self, client, pending):
        client.post(f'/api/v1/commitments/{pending.id}/confirm/')
        pending.refresh_from_db()
        assert pending.reviewed_at is not None

    def test_logs_confirmed_feedback(self, client, pending):
        client.post(f'/api/v1/commitments/{pending.id}/confirm/')
        fb = ExtractionFeedback.objects.get(commitment=pending)
        assert fb.feedback_type == ExtractionFeedback.FeedbackType.CONFIRMED

    def test_import_feedback_sets_from_import_flag(self, org, meeting, client):
        c = Commitment.objects.create(
            organisation=org, meeting=meeting,
            raw_text='x', normalised_text='x', confidence=0.9,
            status=Commitment.Status.PENDING_REVIEW,
            source=Commitment.Source.IMPORT,
        )
        client.post(f'/api/v1/commitments/{c.id}/confirm/')
        fb = ExtractionFeedback.objects.get(commitment=c)
        assert fb.from_import is True

    def test_non_pending_returns_409(self, client, active):
        resp = client.post(f'/api/v1/commitments/{active.id}/confirm/')
        assert resp.status_code == 409

    def test_unauthenticated_returns_401(self, pending):
        resp = APIClient().post(f'/api/v1/commitments/{pending.id}/confirm/')
        assert resp.status_code == 401


# ── reject ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestReject:
    def test_transitions_to_cancelled(self, client, pending):
        resp = client.post(f'/api/v1/commitments/{pending.id}/reject/')
        assert resp.status_code == 200
        assert resp.data['status'] == 'cancelled'

    def test_logs_rejected_feedback(self, client, pending):
        client.post(f'/api/v1/commitments/{pending.id}/reject/')
        fb = ExtractionFeedback.objects.get(commitment=pending)
        assert fb.feedback_type == ExtractionFeedback.FeedbackType.REJECTED

    def test_accepts_note(self, client, pending):
        client.post(
            f'/api/v1/commitments/{pending.id}/reject/',
            {'note': 'not a real commitment'}, format='json',
        )
        fb = ExtractionFeedback.objects.get(commitment=pending)
        assert fb.note == 'not a real commitment'

    def test_non_pending_returns_409(self, client, active):
        resp = client.post(f'/api/v1/commitments/{active.id}/reject/')
        assert resp.status_code == 409

    def test_commitment_still_exists_after_reject(self, client, pending):
        client.post(f'/api/v1/commitments/{pending.id}/reject/')
        assert Commitment.objects.filter(pk=pending.pk).exists()


# ── escalate ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEscalate:
    def test_sets_escalated_status(self, client, active):
        resp = client.post(f'/api/v1/commitments/{active.id}/escalate/')
        assert resp.status_code == 200
        assert resp.data['status'] == 'escalated'

    def test_creates_escalation_event(self, client, active):
        client.post(f'/api/v1/commitments/{active.id}/escalate/')
        assert EscalationEvent.objects.filter(commitment=active).count() == 1

    def test_event_method_is_manual(self, client, active):
        client.post(f'/api/v1/commitments/{active.id}/escalate/')
        evt = EscalationEvent.objects.get(commitment=active)
        assert evt.method == EscalationEvent.Method.MANUAL

    def test_escalate_from_pending_review(self, client, pending):
        resp = client.post(f'/api/v1/commitments/{pending.id}/escalate/')
        assert resp.status_code == 200
        assert resp.data['status'] == 'escalated'

    def test_delivered_returns_409(self, client, delivered):
        resp = client.post(f'/api/v1/commitments/{delivered.id}/escalate/')
        assert resp.status_code == 409

    def test_cancelled_returns_409(self, client, org, meeting):
        c = Commitment.objects.create(
            organisation=org, meeting=meeting,
            raw_text='x', normalised_text='x', confidence=0.9,
            status=Commitment.Status.CANCELLED,
        )
        resp = client.post(f'/api/v1/commitments/{c.id}/escalate/')
        assert resp.status_code == 409

    def test_response_includes_escalations(self, client, active):
        resp = client.post(f'/api/v1/commitments/{active.id}/escalate/')
        assert 'escalations' in resp.data
        assert len(resp.data['escalations']) == 1


# ── resolve ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestResolve:
    def test_delivered(self, client, active):
        resp = client.post(
            f'/api/v1/commitments/{active.id}/resolve/',
            {'outcome': 'delivered'}, format='json',
        )
        assert resp.status_code == 200
        assert resp.data['status'] == 'delivered'

    def test_deferred(self, client, active):
        resp = client.post(
            f'/api/v1/commitments/{active.id}/resolve/',
            {'outcome': 'deferred'}, format='json',
        )
        assert resp.data['status'] == 'deferred'

    def test_cancelled(self, client, active):
        resp = client.post(
            f'/api/v1/commitments/{active.id}/resolve/',
            {'outcome': 'cancelled'}, format='json',
        )
        assert resp.data['status'] == 'cancelled'

    def test_sets_resolved_at(self, client, active):
        client.post(
            f'/api/v1/commitments/{active.id}/resolve/',
            {'outcome': 'delivered'}, format='json',
        )
        active.refresh_from_db()
        assert active.resolved_at is not None

    def test_stores_note(self, client, active):
        client.post(
            f'/api/v1/commitments/{active.id}/resolve/',
            {'outcome': 'deferred', 'note': 'waiting on finance'}, format='json',
        )
        active.refresh_from_db()
        assert active.resolution_note == 'waiting on finance'

    def test_with_new_deadline(self, client, active):
        resp = client.post(
            f'/api/v1/commitments/{active.id}/resolve/',
            {'outcome': 'deferred', 'new_deadline': '2026-09-01'}, format='json',
        )
        assert resp.status_code == 200
        active.refresh_from_db()
        assert str(active.deadline) == '2026-09-01'

    def test_already_delivered_returns_409(self, client, delivered):
        resp = client.post(
            f'/api/v1/commitments/{delivered.id}/resolve/',
            {'outcome': 'cancelled'}, format='json',
        )
        assert resp.status_code == 409

    def test_missing_outcome_returns_400(self, client, active):
        resp = client.post(
            f'/api/v1/commitments/{active.id}/resolve/', {}, format='json',
        )
        assert resp.status_code == 400

    def test_invalid_outcome_returns_400(self, client, active):
        resp = client.post(
            f'/api/v1/commitments/{active.id}/resolve/',
            {'outcome': 'vanished'}, format='json',
        )
        assert resp.status_code == 400
