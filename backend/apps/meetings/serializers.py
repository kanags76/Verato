from rest_framework import serializers
from .models import Meeting


class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = [
            'id', 'title', 'platform', 'occurred_at',
            'processing_status', 'processed_at', 'processing_error',
            'word_count', 'external_id', 'external_url', 'created_at',
        ]
        read_only_fields = [
            'id', 'processing_status', 'processed_at',
            'processing_error', 'word_count', 'created_at',
        ]
