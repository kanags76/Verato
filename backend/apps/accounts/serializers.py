from django.utils.text import slugify
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Organisation, Person, Invitation


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Accept 'email' instead of 'username' for login."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'] = serializers.EmailField(write_only=True)
        del self.fields['username']

    def validate(self, attrs):
        from .models import User
        email = attrs.pop('email', '').lower()
        try:
            user = User.objects.get(email__iexact=email)
            attrs['username'] = user.username
        except User.DoesNotExist:
            attrs['username'] = email  # will fail authentication naturally
        return super().validate(attrs)


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = ['id', 'name', 'slug', 'plan', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']


# ── Auth serializers ──────────────────────────────────────────────────────────

class RegisterSerializer(serializers.Serializer):
    name     = serializers.CharField(max_length=255)
    email    = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    plan     = serializers.ChoiceField(choices=['individual', 'team'])
    org_name = serializers.CharField(max_length=255)

    def validate_email(self, value):
        from .models import User
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value.lower()

    def validate_org_name(self, value):
        slug = slugify(value)
        if not slug:
            raise serializers.ValidationError('Organisation name must produce a valid slug.')
        if Organisation.objects.filter(slug=slug).exists():
            raise serializers.ValidationError('An organisation with this name already exists.')
        return value


class InviteSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower()


class AcceptInviteSerializer(serializers.Serializer):
    token    = serializers.CharField()
    name     = serializers.CharField(max_length=255)
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_token(self, value):
        try:
            invite = Invitation.objects.select_related('organisation').get(token=value)
        except Invitation.DoesNotExist:
            raise serializers.ValidationError('Invalid or unknown invite token.')
        if not invite.is_valid:
            raise serializers.ValidationError('This invite has expired or has already been used.')
        return value


class LinkSlackSerializer(serializers.Serializer):
    slack_user_id = serializers.CharField(max_length=64)


class OrgSettingsSerializer(serializers.Serializer):
    confidence_threshold = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    nudge_hours_before   = serializers.IntegerField(required=False, min_value=1, max_value=168)
    digest_day           = serializers.ChoiceField(
        required=False, choices=['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    )
    digest_hour          = serializers.IntegerField(required=False, min_value=0, max_value=23)


class PersonSerializer(serializers.ModelSerializer):
    recent_topics = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = [
            'id', 'name', 'email', 'role',
            'slack_user_id', 'zoom_user_id',
            'delivery_rate', 'avg_days_late', 'total_commitments',
            'first_seen_at', 'meeting_count', 'recent_topics',
            'created_at',
        ]
        read_only_fields = [
            'id', 'delivery_rate', 'avg_days_late', 'total_commitments',
            'first_seen_at', 'meeting_count', 'recent_topics', 'created_at',
        ]

    def get_recent_topics(self, obj):
        from django.db.models import Count
        from apps.commitments.models import Commitment
        tags = (
            Commitment.objects
            .filter(owner=obj)
            .values('tags__label')
            .annotate(count=Count('id'))
            .filter(tags__label__isnull=False)
            .order_by('-count')[:5]
        )
        return [row['tags__label'] for row in tags]
