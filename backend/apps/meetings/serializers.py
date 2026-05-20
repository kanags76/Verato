from rest_framework import serializers
from .models import Meeting, MeetingTopic


class MeetingTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingTopic
        fields = ['label', 'confidence']


class MeetingSerializer(serializers.ModelSerializer):
    topics           = MeetingTopicSerializer(many=True, read_only=True)
    commitment_count = serializers.SerializerMethodField()
    pending_count    = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = [
            'id', 'title', 'platform', 'occurred_at',
            'meeting_type', 'summary', 'topics',
            'processing_status', 'processed_at', 'processing_error',
            'word_count', 'external_id', 'external_url', 'created_at',
            'commitment_count', 'pending_count',
        ]
        read_only_fields = [
            'id', 'processing_status', 'processed_at',
            'processing_error', 'word_count', 'created_at',
            'topics', 'commitment_count', 'pending_count',
        ]

    def get_commitment_count(self, obj):
        return obj.commitments.count()

    def get_pending_count(self, obj):
        from apps.commitments.models import Commitment
        return obj.commitments.filter(status=Commitment.Status.PENDING_REVIEW).count()


class MeetingStatusSerializer(serializers.Serializer):
    meeting_id       = serializers.UUIDField()
    status           = serializers.CharField()
    processed_at     = serializers.DateTimeField(allow_null=True)
    processing_error = serializers.CharField(allow_null=True)
    commitment_count = serializers.IntegerField()


class MeetingUploadSerializer(serializers.Serializer):
    title        = serializers.CharField(max_length=500)
    occurred_at  = serializers.DateTimeField()
    participants = serializers.CharField(
        required=False, default='', allow_blank=True,
        help_text='Comma-separated participant names e.g. "Sarah K., Tom R., Maya L."',
    )
    transcript = serializers.CharField(
        required=False, allow_blank=True,
        help_text='Paste full transcript text here (alternative to file upload)',
    )
    file = serializers.FileField(
        required=False,
        help_text='Upload transcript file (.txt, .vtt, .srt)',
    )

    def validate(self, data):
        if not data.get('transcript') and not data.get('file'):
            raise serializers.ValidationError(
                'Provide either transcript text or a file upload.'
            )
        return data


class ParticipantMappingItemSerializer(serializers.Serializer):
    detected_name = serializers.CharField(
        help_text='Speaker name as detected in the transcript')
    person_id     = serializers.UUIDField(required=False, allow_null=True,
        help_text='Link to an existing Person in the org')
    person        = serializers.DictField(required=False, allow_null=True,
        help_text='Create a new Person: {name, email?, role?}')
    skip          = serializers.BooleanField(required=False, default=False,
        help_text='True to ignore this speaker (not tracked)')

    def validate(self, attrs):
        has_person_id = bool(attrs.get('person_id'))
        has_person    = bool(attrs.get('person'))
        skip          = attrs.get('skip', False)
        if not skip and not has_person_id and not has_person:
            raise serializers.ValidationError(
                'Each entry must have person_id, person, or skip=true.')
        if has_person_id and has_person:
            raise serializers.ValidationError('Provide person_id OR person, not both.')
        return attrs


class LinkParticipantsSerializer(serializers.Serializer):
    participants = ParticipantMappingItemSerializer(many=True, min_length=1)


class MeetingImportSerializer(serializers.Serializer):
    title = serializers.CharField(
        max_length=500, required=False, default='Prior Commitments Import',
    )
    text = serializers.CharField(
        required=False, allow_blank=True,
        help_text='Paste document text (Notion export, spreadsheet, action list, etc.)',
    )
    file = serializers.FileField(
        required=False,
        help_text='Upload document file (.txt, .csv, .md)',
    )

    def validate(self, data):
        if not data.get('text') and not data.get('file'):
            raise serializers.ValidationError(
                'Provide either document text or a file upload.'
            )
        return data
