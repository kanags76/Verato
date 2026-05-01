from rest_framework import serializers
from .models import Organisation, Person


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = ['id', 'name', 'slug', 'created_at', 'settings']
        read_only_fields = ['id', 'created_at']


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = [
            'id', 'name', 'email', 'role',
            'slack_user_id', 'zoom_user_id',
            'delivery_rate', 'avg_days_late', 'total_commitments',
            'created_at',
        ]
        read_only_fields = ['id', 'delivery_rate', 'avg_days_late', 'total_commitments', 'created_at']
