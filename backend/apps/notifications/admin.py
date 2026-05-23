from django.contrib import admin
from django.urls import path
from django.utils.html import format_html, mark_safe

from .models import NudgeLog, NudgeDashboard


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
