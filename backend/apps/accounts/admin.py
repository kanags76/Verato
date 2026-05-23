from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Invitation, Organisation, Person, User


class OrganisationAdminForm(forms.ModelForm):
    FIRST_DAYS_CHOICES  = [(1, '1 day before'), (2, '2 days before'), (5, '5 days before')]
    SECOND_HOURS_CHOICES = [(24, '24 hours before'), (48, '48 hours before'), (72, '72 hours before')]

    nudge_enabled = forms.BooleanField(
        required=False,
        label='Enable Slack nudges',
        help_text='Send automatic Slack DMs to owners on the configured schedule (09:00 UTC daily).',
    )
    nudge_first_days_before = forms.ChoiceField(
        choices=FIRST_DAYS_CHOICES, required=False, initial=2,
        label='First reminder',
        help_text='Days before deadline to send the first nudge.',
    )
    nudge_second_hours_before = forms.ChoiceField(
        choices=SECOND_HOURS_CHOICES, required=False, initial=48,
        label='Second reminder',
        help_text='Hours before deadline to send the second nudge.',
    )
    gmail_polling_enabled = forms.BooleanField(
        required=False,
        label='Enable Gmail reply polling',
        help_text='Check Gmail nudge threads for owner replies and auto-update commitments.',
    )
    GMAIL_INTERVAL_CHOICES = [(15, 'Every 15 minutes'), (30, 'Every 30 minutes'),
                              (60, 'Every hour'), (120, 'Every 2 hours')]
    gmail_poll_interval_minutes = forms.ChoiceField(
        choices=GMAIL_INTERVAL_CHOICES, required=False, initial=30,
        label='Gmail poll frequency',
        help_text='How often to check for email replies from owners.',
    )

    class Meta:
        model  = Organisation
        fields = ['name', 'slug', 'settings']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            s = self.instance.settings or {}
            self.fields['nudge_enabled'].initial             = s.get('nudge_enabled', False)
            self.fields['nudge_first_days_before'].initial   = s.get('nudge_first_days_before', 2)
            self.fields['nudge_second_hours_before'].initial = s.get('nudge_second_hours_before', 48)
            self.fields['gmail_polling_enabled'].initial         = s.get('gmail_polling_enabled', False)
            self.fields['gmail_poll_interval_minutes'].initial   = s.get('gmail_poll_interval_minutes', 30)

    def save(self, commit=True):
        instance = super().save(commit=False)
        s = instance.settings or {}
        s['nudge_enabled']             = bool(self.cleaned_data.get('nudge_enabled', False))
        s['nudge_first_days_before']   = int(self.cleaned_data['nudge_first_days_before'])
        s['nudge_second_hours_before'] = int(self.cleaned_data['nudge_second_hours_before'])
        s['gmail_polling_enabled']         = bool(self.cleaned_data.get('gmail_polling_enabled', False))
        s['gmail_poll_interval_minutes']   = int(self.cleaned_data.get('gmail_poll_interval_minutes', 30))
        instance.settings = s
        if commit:
            instance.save()
        return instance


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    form          = OrganisationAdminForm
    list_display  = ['name', 'slug', 'slack_connected', 'gmail_connected',
                     'nudges_enabled', 'gmail_polling', 'gmail_poll_interval',
                     'nudge_first_days', 'nudge_second_hours', 'created_at']
    search_fields = ['name', 'slug']
    fieldsets = [
        (None, {'fields': ['name', 'slug']}),
        ('Slack Nudges', {
            'fields': ['nudge_enabled', 'nudge_first_days_before', 'nudge_second_hours_before'],
            'description': 'Post-due nudges (day +1, +2, +3) and CoS escalation on day +1 are always active when enabled.',
        }),
        ('Gmail', {
            'fields': ['gmail_polling_enabled', 'gmail_poll_interval_minutes'],
            'description': 'Gmail must be connected by the org via OAuth before polling will work.',
        }),
    ]

    @admin.display(description='Slack', boolean=True)
    def slack_connected(self, obj):
        return bool((obj.settings or {}).get('slack_token'))

    @admin.display(description='Gmail', boolean=True)
    def gmail_connected(self, obj):
        return bool((obj.settings or {}).get('gmail_refresh_token'))

    @admin.display(description='Slack nudges', boolean=True)
    def nudges_enabled(self, obj):
        return bool((obj.settings or {}).get('nudge_enabled', False))

    @admin.display(description='Gmail polling', boolean=True)
    def gmail_polling(self, obj):
        return bool((obj.settings or {}).get('gmail_polling_enabled', False))

    @admin.display(description='Poll every')
    def gmail_poll_interval(self, obj):
        mins = (obj.settings or {}).get('gmail_poll_interval_minutes', 30)
        return f'{mins} min' if mins < 60 else f'{mins // 60}h'

    @admin.display(description='1st nudge')
    def nudge_first_days(self, obj):
        days = (obj.settings or {}).get('nudge_first_days_before', 2)
        return f'{days}d before'

    @admin.display(description='2nd nudge')
    def nudge_second_hours(self, obj):
        hours = (obj.settings or {}).get('nudge_second_hours_before', 48)
        return f'{hours}h before'


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display  = ['username', 'email', 'organisation', 'is_staff']
    list_filter   = ['organisation', 'is_staff']
    fieldsets     = UserAdmin.fieldsets + (
        ('Organisation', {'fields': ('organisation',)}),
    )


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display  = ['name', 'organisation', 'meeting_count', 'delivery_rate', 'first_seen_at']
    list_filter   = ['organisation']
    search_fields = ['name', 'email']


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display    = ['email', 'organisation', 'invited_by', 'accepted_at', 'expires_at', 'created_at']
    list_filter     = ['organisation']
    search_fields   = ['email']
    readonly_fields = ['token', 'created_at']
