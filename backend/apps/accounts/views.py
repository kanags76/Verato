import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.commitments.models import Commitment

from .models import Invitation, Organisation, Person, User
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    AcceptInviteSerializer,
    EmailTokenObtainPairSerializer,
    InviteSerializer,
    LinkSlackSerializer,
    OrgSettingsSerializer,
    PersonSerializer,
    RegisterSerializer,
)


@extend_schema(tags=['auth'], summary='Login with email + password → JWT tokens')
class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer

logger = logging.getLogger(__name__)


def get_user_org(request):
    return getattr(request.user, 'organisation', None)


def _issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


# ── Auth / onboarding views ───────────────────────────────────────────────────

@extend_schema(
    tags=['auth'],
    summary='Logout — blacklist the refresh token',
    request=inline_serializer('LogoutRequest', fields={'refresh': drf_serializers.CharField()}),
    responses={204: None},
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': 'refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return Response({'detail': 'Token is invalid or already blacklisted.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=['auth'],
    summary='Register a new organisation and admin user',
    request=RegisterSerializer,
    responses={201: inline_serializer('TokenResponse', fields={
        'access':  drf_serializers.CharField(),
        'refresh': drf_serializers.CharField(),
    })},
)
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            org = Organisation.objects.create(
                name=data['org_name'],
                slug=slugify(data['org_name']),
                plan=data['plan'],
            )
            name_parts = data['name'].split(maxsplit=1)
            user = User.objects.create_user(
                username=data['email'],
                email=data['email'],
                password=data['password'],
                first_name=name_parts[0],
                last_name=name_parts[1] if len(name_parts) > 1 else '',
                organisation=org,
                is_org_admin=True,
            )
            Person.objects.create(
                organisation=org,
                user=user,
                name=data['name'],
                email=data['email'],
            )

        return Response({**_issue_tokens(user), 'is_first_login': True}, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['auth'],
    summary='Send an email invite to join your organisation',
    request=InviteSerializer,
    responses={200: inline_serializer('InviteResponse', fields={'detail': drf_serializers.CharField()})},
)
class InviteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_org_admin:
            return Response(
                {'detail': 'Only org admins can send invites.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        org = get_user_org(request)
        if org is None:
            return Response(
                {'detail': 'User has no organisation.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = InviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        if User.objects.filter(organisation=org, email__iexact=email).exists():
            return Response(
                {'detail': 'This email is already a member of your organisation.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invite = _upsert_invite(org, email, request.user)
        _send_invite_email(invite)

        return Response({'detail': 'Invite sent.'}, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['auth'],
    summary='Validate an invite token (returns email + org name)',
    responses={200: inline_serializer('ValidateInviteResponse', fields={
        'email':    drf_serializers.CharField(),
        'org_name': drf_serializers.CharField(),
    })},
)
class ValidateInviteView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token', '')
        try:
            invite = Invitation.objects.select_related('organisation').get(token=token)
        except Invitation.DoesNotExist:
            return Response({'detail': 'Invalid token.'}, status=status.HTTP_404_NOT_FOUND)

        if not invite.is_valid:
            return Response(
                {'detail': 'Invite has expired or already been used.'},
                status=status.HTTP_410_GONE,
            )

        return Response({
            'email':    invite.email,
            'org_name': invite.organisation.name,
        })


@extend_schema(
    tags=['auth'],
    summary='Accept an invite and create your account',
    request=AcceptInviteSerializer,
    responses={201: inline_serializer('AcceptInviteTokenResponse', fields={
        'access':  drf_serializers.CharField(),
        'refresh': drf_serializers.CharField(),
    })},
)
class AcceptInviteView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AcceptInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        invite = Invitation.objects.select_related('organisation').get(token=data['token'])
        org = invite.organisation

        name_parts = data['name'].split(maxsplit=1)
        with transaction.atomic():
            user = User.objects.create_user(
                username=invite.email,
                email=invite.email,
                password=data['password'],
                first_name=name_parts[0],
                last_name=name_parts[1] if len(name_parts) > 1 else '',
                organisation=org,
                is_org_admin=False,
            )
            Person.objects.create(
                organisation=org,
                user=user,
                name=data['name'],
                email=invite.email,
            )
            invite.accepted_at = timezone.now()
            invite.save(update_fields=['accepted_at'])

        return Response(_issue_tokens(user), status=status.HTTP_201_CREATED)


# ── Person ViewSet ────────────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(tags=['persons'], summary='List org participants'),
    retrieve=extend_schema(tags=['persons'], summary='Person detail + delivery stats + lineage'),
    timeline=extend_schema(tags=['persons'], summary='Chronological meetings + commitments for a person'),
    topics=extend_schema(tags=['persons'], summary='Tag frequency list for a person'),
    link_slack=extend_schema(tags=['persons'], summary='Link a Slack user ID to this person'),
)
class PersonViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org = get_user_org(self.request)
        if org is None:
            return Person.objects.none()
        return Person.objects.filter(organisation=org).order_by('name')

    @action(detail=True, methods=['post'], url_path='link-slack')
    def link_slack(self, request, pk=None):
        person = self.get_object()
        is_own = (
            hasattr(request.user, 'person') and
            request.user.person.pk == person.pk
        )
        if not is_own and not request.user.is_org_admin:
            return Response(
                {'detail': 'You can only link your own Slack account.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = LinkSlackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        person.slack_user_id = serializer.validated_data['slack_user_id']
        person.save(update_fields=['slack_user_id'])
        return Response(PersonSerializer(person).data)

    @action(detail=True, methods=['get'], url_path='timeline')
    def timeline(self, request, pk=None):
        org = get_user_org(request)
        if org is None:
            return Response({'detail': 'User has no organisation.'}, status=status.HTTP_403_FORBIDDEN)

        person = self.get_object()

        from apps.meetings.models import Meeting
        from django.db.models import Prefetch

        meetings_qs = (
            Meeting.objects
            .filter(
                organisation=org,
                participants__id=person.pk,
                processing_status=Meeting.ProcessingStatus.COMPLETE,
            )
            .prefetch_related(
                'topics',
                Prefetch(
                    'commitments',
                    queryset=Commitment.objects.filter(owner=person).prefetch_related('tags'),
                    to_attr='person_commitments',
                ),
            )
            .order_by('occurred_at')
        )

        timeline = []
        for meeting in meetings_qs:
            timeline.append({
                'meeting': {
                    'id':           str(meeting.id),
                    'title':        meeting.title,
                    'occurred_at':  meeting.occurred_at,
                    'meeting_type': meeting.meeting_type,
                    'summary':      meeting.summary,
                },
                'commitments': [
                    {
                        'id':              str(c.id),
                        'normalised_text': c.normalised_text,
                        'status':          c.status,
                        'deadline':        c.deadline,
                        'tags':            list(c.tags.values_list('label', flat=True)),
                    }
                    for c in meeting.person_commitments
                ],
                'topics': [
                    {'label': t.label, 'confidence': t.confidence}
                    for t in meeting.topics.all()
                ],
            })

        return Response({'person': PersonSerializer(person).data, 'timeline': timeline})

    @action(detail=True, methods=['get'], url_path='topics')
    def topics(self, request, pk=None):
        from django.db.models import Count, Max

        org = get_user_org(request)
        if org is None:
            return Response({'detail': 'User has no organisation.'}, status=status.HTTP_403_FORBIDDEN)

        person = self.get_object()

        tag_counts = (
            Commitment.objects
            .filter(organisation=org, owner=person)
            .values('tags__label')
            .annotate(count=Count('id'), last_seen=Max('meeting__occurred_at'))
            .filter(tags__label__isnull=False)
            .order_by('-count')
        )

        return Response([
            {'label': row['tags__label'], 'count': row['count'], 'last_seen': row['last_seen']}
            for row in tag_counts
        ])


# ── Invitations list ─────────────────────────────────────────────────────────

@extend_schema(
    tags=['auth'],
    summary='List pending invitations for the org (admin only)',
    responses={200: inline_serializer('InvitationListResponse', fields={
        'id':           drf_serializers.UUIDField(),
        'email':        drf_serializers.EmailField(),
        'status':       drf_serializers.CharField(),
        'expires_at':   drf_serializers.DateTimeField(),
        'created_at':   drf_serializers.DateTimeField(),
    }, many=True)},
)
class InvitationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_org_admin:
            return Response(
                {'detail': 'Only org admins can view invitations.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        org = get_user_org(request)
        if org is None:
            return Response([], status=status.HTTP_200_OK)

        invites = (
            Invitation.objects
            .filter(organisation=org)
            .order_by('-created_at')
            .values('id', 'email', 'accepted_at', 'expires_at', 'created_at')
        )
        data = [
            {
                **inv,
                'status': (
                    'accepted' if inv['accepted_at']
                    else 'expired' if inv['expires_at'] < timezone.now()
                    else 'pending'
                ),
            }
            for inv in invites
        ]
        return Response(data)


# ── Org settings ─────────────────────────────────────────────────────────────

_SETTINGS_KEYS = {'confidence_threshold', 'nudge_hours_before', 'digest_day', 'digest_hour'}


@extend_schema(
    tags=['orgs'],
    summary='Update org settings (confidence threshold, nudge timing, digest schedule)',
    request=OrgSettingsSerializer,
    responses={200: OrgSettingsSerializer},
)
class OrgSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        org = get_user_org(request)
        if org is None or str(org.id) != str(pk):
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not request.user.is_org_admin:
            return Response(
                {'detail': 'Only org admins can update settings.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OrgSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for key, value in serializer.validated_data.items():
            org.settings[key] = value
        org.save(update_fields=['settings'])

        return Response({
            'id':   str(org.id),
            'name': org.name,
            'plan': org.plan,
            'settings': {k: v for k, v in (org.settings or {}).items() if k in _SETTINGS_KEYS},
        })


# ── Helpers ───────────────────────────────────────────────────────────────────

def _upsert_invite(org, email, invited_by):
    """Create or refresh an invite for this email. Resets token + expiry if re-inviting."""
    try:
        invite = Invitation.objects.get(organisation=org, email=email)
        invite.token      = secrets.token_urlsafe(32)
        invite.expires_at = timezone.now() + timedelta(days=7)
        invite.invited_by = invited_by
        invite.accepted_at = None
        invite.save(update_fields=['token', 'expires_at', 'invited_by', 'accepted_at'])
    except Invitation.DoesNotExist:
        invite = Invitation.create_for(org, email, invited_by)
    return invite


def _send_invite_email(invite):
    app_url = getattr(settings, 'APP_BASE_URL', 'http://localhost:3000')
    invite_url = f"{app_url}/invite/?token={invite.token}"
    try:
        send_mail(
            subject=f"You've been invited to join {invite.organisation.name} on Verato",
            message=(
                f"Hi,\n\n"
                f"You've been invited to join {invite.organisation.name} on Verato.\n\n"
                f"Click the link below to create your account (expires in 7 days):\n"
                f"{invite_url}\n\n"
                f"If you didn't expect this invitation, you can ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invite.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("Failed to send invite email to %s: %s", invite.email, exc)
        raise
