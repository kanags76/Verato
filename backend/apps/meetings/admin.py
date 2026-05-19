from django.contrib import admin
from .models import Meeting, MeetingParticipant, MeetingTopic


class MeetingParticipantInline(admin.TabularInline):
    model  = MeetingParticipant
    extra  = 0


class MeetingTopicInline(admin.TabularInline):
    model  = MeetingTopic
    extra  = 0
    fields = ['label', 'confidence']


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display   = ['title', 'organisation', 'platform', 'meeting_type', 'processing_status', 'occurred_at']
    list_filter    = ['organisation', 'platform', 'meeting_type', 'processing_status']
    search_fields  = ['title']
    readonly_fields = ['processed_at', 'created_at']
    inlines        = [MeetingParticipantInline, MeetingTopicInline]
