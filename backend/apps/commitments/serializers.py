from rest_framework import serializers
from .models import Commitment, EscalationEvent, ExtractionFeedback


class CommitmentSerializer(serializers.ModelSerializer):
    owner_name   = serializers.SerializerMethodField()
    meeting_title = serializers.SerializerMethodField()
    is_overdue   = serializers.SerializerMethodField()

    class Meta:
        model = Commitment
        fields = [
            'id', 'raw_text', 'normalised_text', 'commit_type', 'confidence',
            'owner', 'owner_name',
            'deadline', 'deadline_inferred',
            'meeting', 'meeting_title', 'source',
            'status', 'risk_score', 'is_overdue',
            'reviewed_at', 'resolved_at', 'resolution_note',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'risk_score', 'status', 'reviewed_at',
            'resolved_at', 'created_at', 'updated_at',
        ]

    def get_owner_name(self, obj):
        return obj.owner.name if obj.owner else None

    def get_meeting_title(self, obj):
        return obj.meeting.title if obj.meeting_id else None

    def get_is_overdue(self, obj):
        return obj.is_overdue()


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
