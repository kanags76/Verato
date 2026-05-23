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

    class Meta:
        db_table        = 'notifications_nudgelog'
        ordering        = ['-nudged_at']
        unique_together = [['commitment', 'nudge_type']]


class NudgeDashboard(NudgeLog):
    """Proxy used solely to add a Nudge Dashboard link in the admin sidebar."""
    class Meta:
        proxy        = True
        app_label    = 'notifications'
        verbose_name = verbose_name_plural = 'Nudge Dashboard'
