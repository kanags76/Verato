from django.contrib import admin
from django.urls import path
from django.utils.html import format_html, mark_safe

from .models import NudgeLog, NudgeDashboard, GmailPollLog, InAppNotification, CalendarEvent, CalendarConnection, ZoomConnection, ZoomRecording


# ── NudgeLog ──────────────────────────────────────────────────────────────────

_TYPE_COLOURS = {
    'first_reminder':  '#3b82f6',
    'second_reminder': '#8b5cf6',
    'overdue_1':       '#f59e0b',
    'overdue_2':       '#ef4444',
    'overdue_3':       '#dc2626',
    'escalation':      '#7f1d1d',
}


@admin.register(NudgeLog)
class NudgeLogAdmin(admin.ModelAdmin):
    list_display    = ['nudged_at_display', 'nudge_type_badge', 'commitment_link',
                       'person_display', 'channel']
    list_filter     = ['nudge_type', 'nudged_at']
    search_fields   = ['commitment__normalised_text', 'person__name', 'channel']
    readonly_fields = ['commitment', 'person', 'nudge_type', 'nudged_at', 'channel']
    ordering        = ['-nudged_at']

    def has_add_permission(self, request):               return False
    def has_change_permission(self, request, obj=None):  return False

    @admin.display(description='Sent at', ordering='nudged_at')
    def nudged_at_display(self, obj):
        return obj.nudged_at.strftime('%-d %b %Y %H:%M')

    @admin.display(description='Type')
    def nudge_type_badge(self, obj):
        colour = _TYPE_COLOURS.get(obj.nudge_type, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:9px;font-size:11px;font-weight:600">{}</span>',
            colour, obj.get_nudge_type_display(),
        )

    @admin.display(description='Commitment')
    def commitment_link(self, obj):
        if not obj.commitment_id:
            return '—'
        text = (obj.commitment.normalised_text or '')[:60]
        return format_html(
            '<a href="/admin/commitments/commitment/{}/change/">{}</a>',
            obj.commitment_id, text,
        )

    @admin.display(description='Person')
    def person_display(self, obj):
        if not obj.person:
            return mark_safe('<span style="color:#6b7280">CoS escalation</span>')
        return obj.person.name


# ── NudgeDashboard ────────────────────────────────────────────────────────────

@admin.register(NudgeDashboard)
class NudgeDashboardAdmin(admin.ModelAdmin):

    def get_urls(self):
        return [
            path('', self.admin_site.admin_view(self.dashboard_view), name='nudgedashboard_changelist'),
        ]

    def changelist_view(self, request, extra_context=None):
        return self.dashboard_view(request)

    def dashboard_view(self, request):
        from django.shortcuts import render
        from apps.accounts.models import Organisation

        type_counts = {}
        for choice, label in NudgeLog.NudgeType.choices:
            type_counts[choice] = {
                'label':  label,
                'count':  NudgeLog.objects.filter(nudge_type=choice).count(),
                'colour': _TYPE_COLOURS.get(choice, '#6b7280'),
            }

        raw_recent = list(
            NudgeLog.objects
            .select_related('commitment', 'person')
            .order_by('-nudged_at')[:20]
        )
        recent = [
            {'obj': n, 'colour': _TYPE_COLOURS.get(n.nudge_type, '#6b7280')}
            for n in raw_recent
        ]

        task_results = []
        try:
            from django_celery_results.models import TaskResult
            task_results = list(
                TaskResult.objects
                .filter(task_name='apps.notifications.tasks.send_deadline_nudges')
                .order_by('-date_done')[:10]
            )
        except Exception:
            pass

        schedule_info = None
        try:
            from django_celery_beat.models import PeriodicTask
            schedule_info = PeriodicTask.objects.filter(
                task='apps.notifications.tasks.send_deadline_nudges'
            ).first()
        except Exception:
            pass

        org_settings_list = []
        for org in Organisation.objects.all():
            s = org.settings or {}
            if s.get('slack_token'):
                org_settings_list.append({
                    'name':         org.name,
                    'first_days':   s.get('nudge_first_days_before', 2),
                    'second_hours': s.get('nudge_second_hours_before', 48),
                })

        context = {
            **self.admin_site.each_context(request),
            'title':             'Nudge Dashboard',
            'type_counts':       type_counts,
            'recent':            recent,
            'task_results':      task_results,
            'schedule_info':     schedule_info,
            'org_settings_list': org_settings_list,
            'type_colours':      _TYPE_COLOURS,
        }
        return render(request, 'admin/notifications/nudge_dashboard.html', context)

    def has_add_permission(self, request):               return False
    def has_change_permission(self, request, obj=None):  return False
    def has_delete_permission(self, request, obj=None):  return False


# ── GmailPollLog ──────────────────────────────────────────────────────────────

@admin.register(GmailPollLog)
class GmailPollLogAdmin(admin.ModelAdmin):
    list_display    = ['polled_at_display', 'organisation', 'threads_checked',
                       'replies_found', 'commitments_updated', 'status_badge']
    list_filter     = ['organisation', 'polled_at']
    readonly_fields = ['organisation', 'polled_at', 'threads_checked',
                       'replies_found', 'commitments_updated', 'error']
    ordering        = ['-polled_at']

    def has_add_permission(self, request):               return False
    def has_change_permission(self, request, obj=None):  return False

    @admin.display(description='Polled at', ordering='polled_at')
    def polled_at_display(self, obj):
        return obj.polled_at.strftime('%-d %b %Y %H:%M')

    @admin.display(description='Status')
    def status_badge(self, obj):
        if obj.error:
            return mark_safe('<span style="background:#ef4444;color:#fff;padding:2px 8px;border-radius:9px;font-size:11px;font-weight:600">Error</span>')
        return mark_safe('<span style="background:#22c55e;color:#fff;padding:2px 8px;border-radius:9px;font-size:11px;font-weight:600">OK</span>')


# ── InAppNotification ─────────────────────────────────────────────────────────

@admin.register(InAppNotification)
class InAppNotificationAdmin(admin.ModelAdmin):
    list_display    = ['created_at_display', 'organisation', 'notification_type', 'is_read', 'short_message', 'commitment']
    list_filter     = ['organisation', 'notification_type', 'is_read']
    readonly_fields = ['id', 'organisation', 'commitment', 'message', 'notification_type', 'is_read', 'created_at']
    ordering        = ['-created_at']

    def has_add_permission(self, request):               return False
    def has_change_permission(self, request, obj=None):  return False

    @admin.display(description='Created', ordering='created_at')
    def created_at_display(self, obj):
        return obj.created_at.strftime('%-d %b %Y %H:%M')

    @admin.display(description='Message')
    def short_message(self, obj):
        return obj.message[:80]


# ── CalendarConnection ────────────────────────────────────────────────────────

@admin.register(CalendarConnection)
class CalendarConnectionAdmin(admin.ModelAdmin):
    list_display    = ['organisation', 'calendar_email', 'transcripts_badge',
                       'last_synced_at_display', 'connected_at']
    list_filter     = ['transcripts_detected']
    readonly_fields = ['id', 'organisation', 'calendar_email', 'connected_at',
                       'last_synced_at', 'transcripts_detected', 'access_token', 'refresh_token', 'token_expiry']
    ordering        = ['-connected_at']

    def has_add_permission(self, request):               return False
    def has_change_permission(self, request, obj=None):  return False

    @admin.display(description='Last synced', ordering='last_synced_at')
    def last_synced_at_display(self, obj):
        return obj.last_synced_at.strftime('%-d %b %Y %H:%M') if obj.last_synced_at else '—'

    @admin.display(description='Transcripts')
    def transcripts_badge(self, obj):
        if obj.transcripts_detected is True:
            return mark_safe('<span style="background:#22c55e;color:#fff;padding:2px 8px;border-radius:9px;font-size:11px;font-weight:600">Detected</span>')
        if obj.transcripts_detected is False:
            return mark_safe('<span style="background:#f59e0b;color:#fff;padding:2px 8px;border-radius:9px;font-size:11px;font-weight:600">Not detected</span>')
        return mark_safe('<span style="background:#6b7280;color:#fff;padding:2px 8px;border-radius:9px;font-size:11px;font-weight:600">Unknown</span>')


# ── CalendarEvent ─────────────────────────────────────────────────────────────

_EVENT_STATUS_COLOURS = {
    'pending':       '#6b7280',
    'fetching':      '#3b82f6',
    'processing':    '#8b5cf6',
    'done':          '#22c55e',
    'no_transcript': '#f59e0b',
    'failed':        '#ef4444',
}


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display    = ['starts_at_display', 'title', 'organisation', 'status_badge',
                       'meeting_link', 'drive_file_id_short', 'updated_at']
    list_filter     = ['status', 'organisation']
    search_fields   = ['title', 'google_event_id', 'meet_code']
    readonly_fields = ['id', 'organisation', 'google_event_id', 'title', 'starts_at', 'ends_at',
                       'meet_link', 'meet_code', 'status', 'drive_file_id', 'meeting', 'error',
                       'created_at', 'updated_at']
    ordering        = ['-starts_at']

    def has_add_permission(self, request):               return False
    def has_change_permission(self, request, obj=None):  return False

    @admin.display(description='Starts at', ordering='starts_at')
    def starts_at_display(self, obj):
        return obj.starts_at.strftime('%-d %b %Y %H:%M')

    @admin.display(description='Status')
    def status_badge(self, obj):
        colour = _EVENT_STATUS_COLOURS.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:9px;font-size:11px;font-weight:600">{}</span>',
            colour, obj.get_status_display(),
        )

    @admin.display(description='Meeting')
    def meeting_link(self, obj):
        if not obj.meeting_id:
            return '—'
        return format_html(
            '<a href="/admin/meetings/meeting/{}/change/">{}</a>',
            obj.meeting_id, str(obj.meeting_id)[:8],
        )

    @admin.display(description='Drive file')
    def drive_file_id_short(self, obj):
        if not obj.drive_file_id:
            return '—'
        return obj.drive_file_id[:16] + '…'


# ── ZoomConnection ────────────────────────────────────────────────────────────

@admin.register(ZoomConnection)
class ZoomConnectionAdmin(admin.ModelAdmin):
    list_display    = ['organisation', 'zoom_email', 'zoom_account_id',
                       'last_event_at_display', 'connected_at']
    readonly_fields = ['id', 'organisation', 'zoom_email', 'zoom_account_id',
                       'connected_at', 'last_event_at', 'access_token', 'refresh_token', 'token_expiry']
    ordering        = ['-connected_at']

    def has_add_permission(self, request):               return False
    def has_change_permission(self, request, obj=None):  return False

    @admin.display(description='Last webhook', ordering='last_event_at')
    def last_event_at_display(self, obj):
        return obj.last_event_at.strftime('%-d %b %Y %H:%M') if obj.last_event_at else '—'


# ── ZoomRecording ─────────────────────────────────────────────────────────────

_ZOOM_STATUS_COLOURS = {
    'pending':       '#6b7280',
    'fetching':      '#3b82f6',
    'processing':    '#8b5cf6',
    'done':          '#22c55e',
    'no_transcript': '#f59e0b',
    'failed':        '#ef4444',
}


@admin.register(ZoomRecording)
class ZoomRecordingAdmin(admin.ModelAdmin):
    list_display    = ['started_at_display', 'title', 'organisation', 'status_badge',
                       'duration_mins', 'meeting_link', 'updated_at']
    list_filter     = ['status', 'organisation']
    search_fields   = ['title', 'zoom_meeting_id', 'zoom_meeting_uuid']
    readonly_fields = ['id', 'organisation', 'zoom_meeting_id', 'zoom_meeting_uuid', 'title',
                       'started_at', 'duration_mins', 'download_url', 'status', 'meeting',
                       'error', 'created_at', 'updated_at']
    ordering        = ['-started_at']

    def has_add_permission(self, request):               return False
    def has_change_permission(self, request, obj=None):  return False

    @admin.display(description='Started at', ordering='started_at')
    def started_at_display(self, obj):
        return obj.started_at.strftime('%-d %b %Y %H:%M')

    @admin.display(description='Status')
    def status_badge(self, obj):
        colour = _ZOOM_STATUS_COLOURS.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:9px;font-size:11px;font-weight:600">{}</span>',
            colour, obj.get_status_display(),
        )

    @admin.display(description='Meeting')
    def meeting_link(self, obj):
        if not obj.meeting_id:
            return '—'
        return format_html(
            '<a href="/admin/meetings/meeting/{}/change/">{}</a>',
            obj.meeting_id, str(obj.meeting_id)[:8],
        )
