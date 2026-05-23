from rest_framework import serializers
from .models import Commitment, CommitmentTag, CommitmentEvent, EscalationEvent, ExtractionFeedback


class TagsField(serializers.Field):
    """Read: list of label strings. Write: list of label strings → get_or_create tags."""
    def to_representation(self, value):
        return list(value.values_list('label', flat=True))

    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise serializers.ValidationError('Expected a list of tag label strings.')
        return [str(label).lower().strip() for label in data if str(label).strip()]


class CommitmentTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommitmentTag
        fields = ['label']


class EscalationEventSerializer(serializers.ModelSerializer):
    escalated_by_name = serializers.SerializerMethodField()
    escalated_to_name = serializers.SerializerMethodField()

    class Meta:
        model = EscalationEvent
        fields = [
            'id', 'method', 'message_sent', 'outcome',
            'escalated_by', 'escalated_by_name',
            'escalated_to', 'escalated_to_name',
            'occurred_at',
        ]
        read_only_fields = ['id', 'occurred_at']

    def get_escalated_by_name(self, obj):
        return obj.escalated_by.name if obj.escalated_by else None

    def get_escalated_to_name(self, obj):
        return obj.escalated_to.name if obj.escalated_to else None


class ExtractionFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractionFeedback
        fields = ['id', 'feedback_type', 'note', 'from_import', 'created_at']
        read_only_fields = ['id', 'created_at']


class CommitmentSerializer(serializers.ModelSerializer):
    owner_name        = serializers.SerializerMethodField()
    meeting_title     = serializers.SerializerMethodField()
    is_overdue        = serializers.SerializerMethodField()
    needs_manual_nudge = serializers.SerializerMethodField()
    urgency           = serializers.SerializerMethodField()
    tags              = TagsField(required=False)
    escalations       = EscalationEventSerializer(many=True, read_only=True)

    class Meta:
        model = Commitment
        fields = [
            'id', 'raw_text', 'normalised_text', 'commit_type', 'confidence',
            'owner', 'owner_name',
            'deadline', 'deadline_inferred',
            'meeting', 'meeting_title', 'source',
            'tags',
            'priority',
            'status', 'risk_score', 'is_overdue',
            'needs_manual_nudge', 'urgency',
            'reviewed_at', 'resolved_at', 'resolution_note',
            'escalations',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'raw_text', 'commit_type', 'confidence',
            'risk_score', 'status', 'reviewed_at',
            'resolved_at', 'created_at', 'updated_at', 'escalations',
        ]

    def get_owner_name(self, obj):
        return obj.owner.name if obj.owner else None

    def get_meeting_title(self, obj):
        return obj.meeting.title if obj.meeting_id else None

    def get_is_overdue(self, obj):
        return obj.is_overdue()

    def get_needs_manual_nudge(self, obj):
        _nudgeable = {'active', 'at_risk', 'escalated', 'deferred'}
        if obj.status not in _nudgeable:
            return False
        if not obj.deadline:
            return False
        return not obj.owner or not obj.owner.slack_user_id

    def get_urgency(self, obj):
        if not obj.deadline:
            return None
        from django.utils import timezone
        days = (obj.deadline - timezone.now().date()).days
        if days < 0:
            return 'overdue'
        if days == 0:
            return 'due_today'
        if days <= 3:
            return 'due_soon'
        return 'upcoming'

    def update(self, instance, validated_data):
        tag_labels = validated_data.pop('tags', None)
        instance = super().update(instance, validated_data)
        if tag_labels is not None:
            org = instance.organisation
            tag_objs = [
                CommitmentTag.objects.get_or_create(organisation=org, label=label)[0]
                for label in tag_labels
            ]
            instance.tags.set(tag_objs)
        return instance


class CommitmentEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = CommitmentEvent
        fields = ['id', 'event_type', 'actor_name', 'old_value', 'new_value', 'note', 'occurred_at']
        read_only_fields = fields

    def get_actor_name(self, obj):
        return obj.actor.name if obj.actor else None


class ResolveSerializer(serializers.Serializer):
    outcome      = serializers.ChoiceField(choices=['done', 'deferred', 'cancelled'])
    note         = serializers.CharField(required=False, allow_blank=True, default='')
    new_deadline = serializers.DateField(required=False, allow_null=True)
