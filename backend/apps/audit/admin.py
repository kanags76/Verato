from django.contrib import admin
from django.utils.html import format_html

from .models import DataAccessGrant


@admin.register(DataAccessGrant)
class DataAccessGrantAdmin(admin.ModelAdmin):
    list_display    = ['organisation', 'granted_by', 'reason_snippet', 'granted_at', 'expires_at', 'status_badge', 'document_link']
    list_filter     = ['organisation', 'is_revoked']
    readonly_fields = ['id', 'granted_by', 'granted_at', 'status_badge', 'document_link']
    ordering        = ['-granted_at']

    fieldsets = [
        (None, {'fields': ['organisation', 'document', 'reason', 'expires_at']}),
        ('Audit', {'fields': ['id', 'granted_by', 'granted_at', 'is_revoked'], 'classes': ['collapse']}),
    ]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description='Reason')
    def reason_snippet(self, obj):
        return obj.reason[:60] + '…' if len(obj.reason) > 60 else obj.reason

    @admin.display(description='Status')
    def status_badge(self, obj):
        if obj.is_revoked:
            colour, label = '#ef4444', 'REVOKED'
        elif obj.is_active:
            colour, label = '#10b981', 'ACTIVE'
        else:
            colour, label = '#6b7280', 'EXPIRED'
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:9px;font-size:11px;font-weight:600">{}</span>',
            colour, label,
        )

    @admin.display(description='Document')
    def document_link(self, obj):
        if obj.document:
            return format_html('<a href="{}" target="_blank">View</a>', obj.document.url)
        return '—'
