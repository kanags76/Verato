import secrets
import uuid
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Organisation(models.Model):
    class Plan(models.TextChoices):
        INDIVIDUAL = 'individual', 'Individual'
        TEAM       = 'team',       'Team'

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=255)
    slug       = models.SlugField(unique=True)
    plan       = models.CharField(max_length=20, choices=Plan.choices, default=Plan.INDIVIDUAL)
    created_at = models.DateTimeField(auto_now_add=True)
    settings   = models.JSONField(default=dict)
    # settings keys: confidence_threshold, nudge_hours_before, digest_day, digest_hour,
    #                slack_token, slack_workspace_id, slack_workspace_name

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'accounts_organisation'


class User(AbstractUser):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE,
        null=True, blank=True, related_name='users'
    )
    is_org_admin = models.BooleanField(default=False)

    class Meta:
        db_table = 'accounts_user'


class Invitation(models.Model):
    """Pending invite sent to a colleague's email address."""
    _TOKEN_EXPIRY_DAYS = 7

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='invitations')
    email        = models.EmailField()
    token        = models.CharField(max_length=64, unique=True)
    invited_by   = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='sent_invitations'
    )
    accepted_at  = models.DateTimeField(null=True, blank=True)
    expires_at   = models.DateTimeField()
    created_at   = models.DateTimeField(auto_now_add=True)

    @classmethod
    def create_for(cls, organisation, email, invited_by):
        return cls.objects.create(
            organisation=organisation,
            email=email,
            token=secrets.token_urlsafe(32),
            invited_by=invited_by,
            expires_at=timezone.now() + timedelta(days=cls._TOKEN_EXPIRY_DAYS),
        )

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_used(self):
        return self.accepted_at is not None

    @property
    def is_valid(self):
        return not self.is_expired and not self.is_used

    def __str__(self):
        return f"Invite → {self.email} ({self.organisation.slug})"

    class Meta:
        db_table = 'accounts_invitation'
        unique_together = [['organisation', 'email']]


class Person(models.Model):
    """
    Anyone who appears in meetings — may or may not have a User account.
    Commitment owners interact via Slack only and never have a User account.
    delivery_rate and avg_days_late are recomputed by Celery after each commitment resolves.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='persons')
    user         = models.OneToOneField(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='person'
    )
    name         = models.CharField(max_length=255)
    email        = models.EmailField(blank=True, null=True)
    role         = models.CharField(max_length=255, blank=True)

    slack_user_id = models.CharField(max_length=64, blank=True)
    zoom_user_id  = models.CharField(max_length=64, blank=True)

    delivery_rate         = models.FloatField(default=1.0)
    avg_days_late         = models.FloatField(default=0.0)
    total_commitments     = models.IntegerField(default=0)
    delivery_rate_updated = models.DateTimeField(null=True, blank=True)

    # Week 3.5 — lineage metadata; maintained by process_meeting Celery task
    first_seen_at = models.DateTimeField(null=True, blank=True)
    meeting_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.organisation.slug})"

    class Meta:
        db_table = 'accounts_person'
        unique_together = [['organisation', 'email']]
        indexes = [
            models.Index(fields=['organisation', 'slack_user_id']),
            models.Index(fields=['organisation', 'first_seen_at']),
        ]


class EmailOTP(models.Model):
    class Purpose(models.TextChoices):
        EMAIL_VERIFICATION = 'email_verification', 'Email Verification'
        PASSWORD_RESET     = 'password_reset',     'Password Reset'

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code       = models.CharField(max_length=6)
    purpose    = models.CharField(max_length=20, choices=Purpose.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at    = models.DateTimeField(null=True, blank=True)
    attempts   = models.IntegerField(default=0)

    class Meta:
        db_table = 'accounts_emailotp'
        indexes = [
            models.Index(fields=['user', 'purpose', 'created_at'], name='emailotp_user_purpose_idx'),
        ]


class MeetingManager(models.Model):
    """
    Two-sided delegation of meeting management access.
    managed_user (the meeting owner) creates the record.
    manager_user must explicitly accept before gaining access.
    Either party can delete: managed_user revokes, manager_user declines or resigns.
    """
    class Status(models.TextChoices):
        PENDING  = 'pending',  'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='meeting_managers')
    manager_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='manages_for')
    managed_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='delegated_to')
    status       = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at   = models.DateTimeField(auto_now_add=True)
    accepted_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table        = 'accounts_meetingmanager'
        unique_together = [['organisation', 'manager_user', 'managed_user']]
