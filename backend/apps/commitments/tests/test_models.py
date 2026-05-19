"""Model tests for CommitmentTag and Commitment.tags M2M."""
import pytest
from django.db import IntegrityError
from django.utils import timezone
from apps.accounts.models import Organisation
from apps.meetings.models import Meeting
from apps.commitments.models import Commitment, CommitmentTag


@pytest.fixture
def org(db):
    return Organisation.objects.create(name='Test Org', slug='test-org')


@pytest.fixture
def meeting(org):
    return Meeting.objects.create(
        organisation=org,
        title='Test Meeting',
        occurred_at=timezone.now(),
    )


@pytest.fixture
def commitment(org, meeting):
    return Commitment.objects.create(
        organisation=org,
        meeting=meeting,
        raw_text='I will send the report.',
        normalised_text='Alice will send the report.',
        confidence=0.9,
        source=Commitment.Source.TRANSCRIPT,
    )


@pytest.mark.django_db
class TestCommitmentTagModel:
    def test_create_tag(self, org):
        tag = CommitmentTag.objects.create(organisation=org, label='q2 board prep')
        assert tag.label == 'q2 board prep'
        assert str(tag) == 'q2 board prep'

    def test_unique_together_org_label(self, org):
        CommitmentTag.objects.create(organisation=org, label='pricing')
        with pytest.raises(IntegrityError):
            CommitmentTag.objects.create(organisation=org, label='pricing')

    def test_same_label_different_orgs_allowed(self, org):
        org2 = Organisation.objects.create(name='Other Org', slug='other-org')
        CommitmentTag.objects.create(organisation=org, label='pricing')
        tag2 = CommitmentTag.objects.create(organisation=org2, label='pricing')
        assert tag2.pk is not None

    def test_get_or_create_deduplication(self, org):
        CommitmentTag.objects.get_or_create(organisation=org, label='hiring')
        CommitmentTag.objects.get_or_create(organisation=org, label='hiring')
        assert CommitmentTag.objects.filter(organisation=org, label='hiring').count() == 1


@pytest.mark.django_db
class TestCommitmentTagsM2M:
    def test_add_tags_to_commitment(self, org, commitment):
        tag1 = CommitmentTag.objects.create(organisation=org, label='pricing')
        tag2 = CommitmentTag.objects.create(organisation=org, label='q2 planning')
        commitment.tags.add(tag1, tag2)
        assert commitment.tags.count() == 2

    def test_commitment_without_tags_returns_empty(self, commitment):
        assert list(commitment.tags.all()) == []

    def test_filter_commitments_by_tag(self, org, meeting):
        tag = CommitmentTag.objects.create(organisation=org, label='hiring')
        c1 = Commitment.objects.create(
            organisation=org, meeting=meeting,
            raw_text='a', normalised_text='a', confidence=0.9,
        )
        c2 = Commitment.objects.create(
            organisation=org, meeting=meeting,
            raw_text='b', normalised_text='b', confidence=0.9,
        )
        c1.tags.add(tag)

        tagged = Commitment.objects.filter(tags__label='hiring')
        assert c1 in tagged
        assert c2 not in tagged

    def test_tags_values_list(self, org, commitment):
        tag = CommitmentTag.objects.create(organisation=org, label='emea pricing')
        commitment.tags.add(tag)
        labels = list(commitment.tags.values_list('label', flat=True))
        assert labels == ['emea pricing']

    def test_existing_commitments_have_no_tags(self, commitment):
        # Regression: pre-3.5 commitments default to empty M2M — no error
        assert commitment.tags.count() == 0
        assert list(commitment.tags.all()) == []
