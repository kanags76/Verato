import uuid
from django.db import models
from apps.commitments.models import Commitment


class NudgeLog(models.Model):
    """
    One row per nudge type per commitment. unique_together prevents re-sending the same
    nudge type twice. Person FK tracks who was nudged (owner vs CoS escalation).
    """

    class NudgeType(models.TextChoices):
        FIRST_REMINDER  = 'first_reminder',  'First Reminder'
        SECOND_REMINDER = 'second_reminder', 'Second Reminder'
        OVERDUE_1       = 'overdue_1',       'Overdue Day +1'
        OVERDUE_2       = 'overdue_2',       'Overdue Day +2'
        OVERDUE_3       = 'overdue_3',       'Overdue Day +3'
        ESCALATION      = 'escalation',      'Escalation to CoS'

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commitment = models.ForeignKey(Commitment, on_delete=models.CASCADE, related_name='nudges')
    person     = models.ForeignKey(
        'accounts.Person', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='nudges_received',
    )
    nudge_type = models.CharField(max_length=20, choices=NudgeType.choices)
    nudged_at  = models.DateTimeField(auto_now_add=True)
    channel    = models.CharField(max_length=64, blank=True)

    gmail_thread_id = models.CharField(max_length=32, blank=True)

    class Meta:
        db_table        = 'notifications_nudgelog'
        ordering        = ['-nudged_at']
        unique_together = [['commitment', 'nudge_type']]


class GmailPollLog(models.Model):
    """One row per poll run per org — tracks what was found and what was updated."""
    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation        = models.ForeignKey('accounts.Organisation', on_delete=models.CASCADE, related_name='gmail_poll_logs')
    polled_at           = models.DateTimeField(auto_now_add=True)
    threads_checked     = models.IntegerField(default=0)
    replies_found       = models.IntegerField(default=0)
    commitments_updated = models.IntegerField(default=0)
    error               = models.TextField(blank=True)

    class Meta:
        db_table = 'notifications_gmailpolllog'
        ordering = ['-polled_at']


class NudgeDashboard(NudgeLog):
    """Proxy used solely to add a Nudge Dashboard link in the admin sidebar."""
    class Meta:
        proxy        = True
        app_label    = 'notifications'
        verbose_name = verbose_name_plural = 'Nudge Dashboard'


class InAppNotification(models.Model):
    """
    Per-user in-app alert. Created when a commitment is updated via Slack button
    click or Gmail reply parse. Frontend polls /api/v1/notifications/ for these.
    """
    class Type(models.TextChoices):
        SLACK_REPLY  = 'slack_reply',  'Slack Reply'
        GMAIL_REPLY  = 'gmail_reply',  'Gmail Reply'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey('accounts.Organisation', on_delete=models.CASCADE, related_name='in_app_notifications')
    commitment   = models.ForeignKey(Commitment, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    message      = models.TextField()
    notification_type = models.CharField(max_length=20, choices=Type.choices)
    is_read      = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications_inappnotification'
        ordering = ['-created_at']
