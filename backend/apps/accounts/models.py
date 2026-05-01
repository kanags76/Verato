import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class Organisation(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=255)
    slug       = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    settings   = models.JSONField(default=dict)
    # settings keys: confidence_threshold (float), nudge_hours_before (int),
    # digest_day (str), digest_hour (int)

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

    class Meta:
        db_table = 'accounts_user'


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
    email        = models.EmailField(blank=True)
    role         = models.CharField(max_length=255, blank=True)

    slack_user_id = models.CharField(max_length=64, blank=True)
    zoom_user_id  = models.CharField(max_length=64, blank=True)

    delivery_rate         = models.FloatField(default=1.0)
    avg_days_late         = models.FloatField(default=0.0)
    total_commitments     = models.IntegerField(default=0)
    delivery_rate_updated = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.organisation.slug})"

    class Meta:
        db_table = 'accounts_person'
        unique_together = [['organisation', 'email']]
        indexes = [
            models.Index(fields=['organisation', 'slack_user_id']),
        ]
