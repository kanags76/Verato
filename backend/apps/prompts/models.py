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
