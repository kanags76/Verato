import uuid
from django.db import models
from django.conf import settings


class Prompt(models.Model):
    """
    Editable Gemini prompts stored in the database.
    Admins can update prompt content without a code deploy.
    version auto-increments on each save so changes are auditable.
    """
    name       = models.CharField(max_length=100, unique=True,
                                  help_text='Slug used by the extraction layer, e.g. transcript_extraction')
    content    = models.TextField()
    version    = models.PositiveIntegerField(default=1, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'prompts_prompt'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} (v{self.version})'


class AICallLog(models.Model):
    """
    Immutable log of every Gemini API call.
    Captures input, output, duration, success, and related domain objects.
    Foundation for eval harness, cost tracking, and prompt regression testing.
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation    = models.ForeignKey(
        'accounts.Organisation', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='ai_call_logs',
    )
    prompt_name     = models.CharField(max_length=100, db_index=True)
    prompt_version  = models.PositiveIntegerField(default=0)
    input_text      = models.TextField()
    output_text     = models.TextField(blank=True)
    duration_ms     = models.PositiveIntegerField()
    success         = models.BooleanField()
    error           = models.TextField(blank=True)
    # Related domain objects stored as bare UUIDs to avoid cross-app FK complexity
    meeting_id      = models.UUIDField(null=True, blank=True, db_index=True)
    commitment_id   = models.UUIDField(null=True, blank=True, db_index=True)
    tag_id          = models.UUIDField(null=True, blank=True)
    triggered_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )
    created_at      = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'prompts_aicalllog'
        ordering = ['-created_at']

    def __str__(self):
        status = 'OK' if self.success else 'FAIL'
        return f'[{status}] {self.prompt_name} v{self.prompt_version} ({self.duration_ms}ms)'
