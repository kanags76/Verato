import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def _default_expiry():
    return timezone.now() + timedelta(days=30)


class DataAccessGrant(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        'accounts.Organisation', on_delete=models.CASCADE, related_name='access_grants',
    )
    granted_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+',
    )
    document     = models.FileField(
        upload_to='data_access_grants/',
        help_text='Upload the permission email or signed acknowledgement (PDF, image, or text file)',
    )
    reason       = models.TextField(help_text='Why is this data being accessed?')
    granted_at   = models.DateTimeField(auto_now_add=True)
    expires_at   = models.DateTimeField(
        default=_default_expiry,
        help_text='Access expires at this datetime (default 30 days from now)',
    )
    is_revoked   = models.BooleanField(default=False)

    class Meta:
        db_table = 'audit_dataaccessgrant'
        ordering = ['-granted_at']

    def __str__(self):
        status = 'ACTIVE' if self.is_active else ('REVOKED' if self.is_revoked else 'EXPIRED')
        return f'{self.organisation} [{status}] — {self.granted_by} — expires {self.expires_at.date()}'

    @property
    def is_active(self):
        return not self.is_revoked and self.expires_at > timezone.now()
