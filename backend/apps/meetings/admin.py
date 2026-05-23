import json

import redis
from django.conf import settings
from django.contrib import admin, messages
from django.http import JsonResponse
from django.urls import path
from django.utils.html import format_html, mark_safe
from django.utils.timezone import now

from apps.audit.helpers import DataAccessMixin
from .models import Meeting, MeetingClarification, MeetingParticipant, MeetingTopic, PipelineStatus


# ── Inlines ───────────────────────────────────────────────────────────────────

class MeetingParticipantInline(admin.TabularInline):
    model = MeetingParticipant
    extra = 0


class MeetingTopicInline(admin.TabularInline):
    model  = MeetingTopic
    extra  = 0
    fields = ['label', 'confidence']


class MeetingClarificationInline(admin.TabularInline):
    model     = MeetingClarification
    extra     = 0
    fields    = ['order', 'question', 'context', 'answer', 'answered_at']
    readonly_fields = ['order', 'question', 'context', 'answered_at']
    ordering  = ['order']


# ── Actions ───────────────────────────────────────────────────────────────────

@admin.action(description='Reprocess selected meetings (requeue Celery task)')
def reprocess_meetings(modeladmin, request, queryset):
    from .tasks import process_meeting, process_import
    requeued = 0
    for meeting in queryset.exclude(
        processing_status=Meeting.ProcessingStatus.PROCESSING
    ):
        meeting.processing_status = Meeting.ProcessingStatus.PENDING
        meeting.processing_error  = ''
        meeting.save(update_fields=['processing_status', 'processing_error'])
        if meeting.platform == Meeting.Platform.IMPORT:
            process_import.delay(str(meeting.id))
        else:
            process_meeting.delay(str(meeting.id))
        requeued += 1
    messages.success(request, f'{requeued} meeting(s) requeued for processing.')


@admin.action(description='Mark selected meetings as Failed')
def mark_failed(modeladmin, request, queryset):
    updated = queryset.update(processing_status=Meeting.ProcessingStatus.FAILED)
    messages.warning(request, f'{updated} meeting(s) marked as Failed.')


@admin.action(description='Reset selected meetings to Pending')
def reset_to_pending(modeladmin, request, queryset):
    updated = queryset.update(
        processing_status=Meeting.ProcessingStatus.PENDING,
        processing_error='',
    )
    messages.success(request, f'{updated} meeting(s) reset to Pending.')


# ── MeetingAdmin ──────────────────────────────────────────────────────────────

@admin.register(Meeting)
class MeetingAdmin(DataAccessMixin, admin.ModelAdmin):
    list_display    = [
        'title_display', 'organisation', 'platform', 'status_badge',
        'word_count_display', 'commitment_count', 'age_minutes', 'error_snippet',
    ]
    list_filter     = ['organisation', 'platform', 'processing_status', 'meeting_type']
    search_fields   = ['title', 'processing_error']
    readonly_fields = ['id', 'processed_at', 'created_at', 'word_count', 'commitment_count_display']
    actions         = [reprocess_meetings, mark_failed, reset_to_pending]
    inlines         = [MeetingParticipantInline, MeetingTopicInline, MeetingClarificationInline]

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('pipeline-status/', self.admin_site.admin_view(self.pipeline_status_view), name='pipeline_status'),
            path('pipeline-status/api/', self.admin_site.admin_view(self.pipeline_status_api), name='pipeline_status_api'),
        ]
        return custom + urls

    # ── List display helpers ──────────────────────────────────────────────────

    _REDACTED = mark_safe('<span style="color:#6b7280;font-style:italic">— redacted —</span>')

    @admin.display(description='Title', ordering='title')
    def title_display(self, obj):
        if not self._has_grant(obj):
            return self._REDACTED
        return obj.title

    @admin.display(description='Words', ordering='word_count')
    def word_count_display(self, obj):
        if not self._has_grant(obj):
            return '—'
        return obj.word_count

    @admin.display(description='Status', ordering='processing_status')
    def status_badge(self, obj):
        colours = {
            'pending':                '#f59e0b',
            'processing':             '#3b82f6',
            'pending_clarification':  '#8b5cf6',
            'complete':               '#10b981',
            'failed':                 '#ef4444',
        }
        colour = colours.get(obj.processing_status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:9px;font-size:11px;font-weight:600">{}</span>',
            colour, obj.processing_status.upper(),
        )

    @admin.display(description='Commitments')
    def commitment_count(self, obj):
        if not self._has_grant(obj):
            return '—'
        return obj.commitments.count()

    @admin.display(description='Age (min)', ordering='created_at')
    def age_minutes(self, obj):
        delta = now() - obj.created_at
        mins  = int(delta.total_seconds() / 60)
        colour = '#ef4444' if mins > 10 and obj.processing_status == 'processing' else 'inherit'
        return format_html('<span style="color:{}">{}</span>', colour, mins)

    @admin.display(description='Error')
    def error_snippet(self, obj):
        if not self._has_grant(obj):
            return '—'
        if not obj.processing_error:
            return '—'
        snippet = obj.processing_error[:80]
        return format_html('<span style="color:#ef4444;font-size:11px" title="{}">{}</span>',
                           obj.processing_error, snippet)

    def commitment_count_display(self, obj):
        return obj.commitments.count()
    commitment_count_display.short_description = 'Commitments extracted'

    # ── Pipeline status views ─────────────────────────────────────────────────

    def _get_pipeline_data(self):
        # Redis queue depths
        queues = {}
        try:
            r = redis.from_url(settings.REDIS_URL)
            for q in ['default', 'extractions', 'notifications']:
                queues[q] = r.llen(q)
        except Exception as exc:
            queues['error'] = str(exc)

        # Recent meetings by status
        statuses = {}
        for s in ['pending', 'processing', 'pending_clarification', 'complete', 'failed']:
            statuses[s] = Meeting.objects.filter(processing_status=s).count()

        # Stuck processing (>10 min in processing state)
        from django.utils.timezone import now
        from datetime import timedelta
        stuck = list(
            Meeting.objects.filter(
                processing_status=Meeting.ProcessingStatus.PROCESSING,
                created_at__lt=now() - timedelta(minutes=10),
            ).values('id', 'title', 'organisation__name', 'created_at')[:20]
        )

        # Recent failures
        failures = list(
            Meeting.objects.filter(
                processing_status=Meeting.ProcessingStatus.FAILED,
            ).order_by('-created_at').values('id', 'title', 'processing_error', 'created_at')[:10]
        )

        return {
            'queues':   queues,
            'queues_list': [
                ('Default',       queues.get('default', 0)),
                ('Extractions',   queues.get('extractions', 0)),
                ('Notifications', queues.get('notifications', 0)),
            ],
            'statuses': statuses,
            'stuck':    stuck,
            'failures': failures,
        }

    def pipeline_status_api(self, request):
        data = self._get_pipeline_data()
        for item in data['stuck'] + data['failures']:
            if 'created_at' in item and item['created_at']:
                item['created_at'] = item['created_at'].strftime('%-d %b %H:%M')
        return JsonResponse({
            'queues_list': data['queues_list'],
            'statuses':    data['statuses'],
            'stuck':       data['stuck'],
            'failures':    data['failures'],
        })

    def pipeline_status_view(self, request):
        from django.shortcuts import render
        data = self._get_pipeline_data()
        context = {
            **self.admin_site.each_context(request),
            'title':       'Pipeline Status',
            'queues_list': data['queues_list'],
            'statuses':    data['statuses'],
            'stuck':       data['stuck'],
            'failures':    data['failures'],
        }
        return render(request, 'admin/meetings/pipeline_status.html', context)


@admin.register(PipelineStatus)
class PipelineStatusAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect
        return redirect('/admin/meetings/meeting/pipeline-status/')

    def has_add_permission(self, request):        return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
