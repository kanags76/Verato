import uuid
from django.db import models
from apps.commitments.models import Commitment


class NudgeLog(models.Model):
    """
    Records every Slack nudge sent so we never double-nudge within the same window.
    One record per nudge attempt — queried before each send_deadline_nudges run.
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commitment = models.ForeignKey(Commitment, on_delete=models.CASCADE, related_name='nudges')
    nudged_at  = models.DateTimeField(auto_now_add=True)
    channel    = models.CharField(max_length=64, blank=True)  # Slack channel/DM id

    class Meta:
        db_table = 'notifications_nudgelog'
        ordering = ['-nudged_at']
