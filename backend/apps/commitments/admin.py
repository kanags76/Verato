from django.contrib import admin
from django.utils.html import format_html, mark_safe

from apps.audit.helpers import DataAccessMixin
from .models import Commitment, CommitmentTag, EscalationEvent, ExtractionFeedback


class EscalationEventInline(admin.TabularInline):
    model         = EscalationEvent
    extra         = 0
    readonly_fields = ['method', 'outcome', 'occurred_at']
    can_delete    = False


@admin.register(Commitment)
class CommitmentAdmin(DataAccessMixin, admin.ModelAdmin):
    list_display   = ['commitment_text', 'organisation', 'owner_display', 'status', 'risk_score', 'deadline', 'source']
    list_filter    = ['organisation', 'status', 'source']
    search_fields  = ['normalised_text', 'raw_text']
    readonly_fields = ['created_at', 'updated_at', 'reviewed_at', 'resolved_at', 'risk_score']
    inlines        = [EscalationEventInline]

    _REDACTED = mark_safe('<span style="color:#6b7280;font-style:italic">— redacted —</span>')

    @admin.display(description='Commitment')
    def commitment_text(self, obj):
        if not self._has_grant(obj):
            return self._REDACTED
        return obj.normalised_text[:80]

    @admin.display(description='Owner')
    def owner_display(self, obj):
        if not self._has_grant(obj):
            return '—'
        return obj.owner


@admin.register(CommitmentTag)
class CommitmentTagAdmin(admin.ModelAdmin):
    list_display  = ['label', 'organisation', 'created_at']
    list_filter   = ['organisation']
    search_fields = ['label']


@admin.register(EscalationEvent)
class EscalationEventAdmin(admin.ModelAdmin):
    list_display  = ['commitment', 'method', 'outcome', 'occurred_at']
    list_filter   = ['method', 'outcome']
    readonly_fields = ['occurred_at']


@admin.register(ExtractionFeedback)
class ExtractionFeedbackAdmin(admin.ModelAdmin):
    list_display  = ['commitment', 'feedback_type', 'from_import', 'created_at']
    list_filter   = ['feedback_type', 'from_import', 'organisation']
    readonly_fields = ['created_at']
