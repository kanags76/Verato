import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core import signing
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

from .models import EmailOTP, Invitation, Organisation, Person, User
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    AcceptInviteSerializer,
    EmailTokenObtainPairSerializer,
    InviteSerializer,
    LinkSlackSerializer,
    MergePersonsSerializer,
    OrgSettingsSerializer,
    PersonSerializer,
    RegisterSerializer,
)


@extend_schema(tags=['auth'], summary='Login with email + password → JWT tokens')
class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer

logger = logging.getLogger(__name__)


# ── Email Verification (registration) ────────────────────────────────────────

@extend_schema(
    tags=['auth'],
    summary='Verify email address after registration — activate account and return JWT',
    request=inline_serializer('VerifyEmailRequest', fields={
        'session_token': drf_serializers.CharField(),
        'code':          drf_serializers.CharField(),
    }),
    responses={200: inline_serializer('VerifyEmailResponse', fields={
        'access':  drf_serializers.CharField(),
        'refresh': drf_serializers.CharField(),
    })},
)
class VerifyEmailView(APIView):
    """Confirm the 6-digit OTP sent during registration, activate the account, return JWT."""
    permission_classes = [AllowAny]

    def post(self, request):
        session_token = request.data.get('session_token', '')
        code          = request.data.get('code', '').strip()

        if not session_token or not code:
            return Response({'detail': 'session_token and code are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = signing.loads(session_token, salt='email-verify', max_age=600)
        except signing.SignatureExpired:
            return Response({'detail': 'Verification link expired. Please register again.'}, status=status.HTTP_400_BAD_REQUEST)
        except signing.BadSignature:
            return Response({'detail': 'Invalid verification token.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id, is_active=False)
        except User.DoesNotExist:
            return Response({'detail': 'Invalid or already verified account.'}, status=status.HTTP_400_BAD_REQUEST)

        otp = (
            EmailOTP.objects
            .filter(user=user, purpose=EmailOTP.Purpose.EMAIL_VERIFICATION, used_at__isnull=True)
            .order_by('-created_at')
            .first()
        )

        if otp is None or timezone.now() > otp.expires_at:
            return Response({'detail': 'Code has expired. Please register again.'}, status=status.HTTP_400_BAD_REQUEST)
        if otp.attempts >= 5:
            return Response({'detail': 'Too many failed attempts. Please register again.'}, status=status.HTTP_400_BAD_REQUEST)

        if otp.code != code:
            otp.attempts += 1
            otp.save(update_fields=['attempts'])
            remaining = 5 - otp.attempts
            return Response(
                {'detail': f'Invalid code. {remaining} attempt(s) remaining.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            otp.used_at = timezone.now()
            otp.save(update_fields=['used_at'])
            user.is_active = True
            user.save(update_fields=['is_active'])

        return Response(_issue_tokens(user))


# ── Resend Verification ───────────────────────────────────────────────────────

@extend_schema(
    tags=['auth'],
    summary='Resend email verification OTP for an unverified account',
    request=inline_serializer('ResendVerificationRequest', fields={'email': drf_serializers.EmailField()}),
    responses={200: inline_serializer('ResendVerificationResponse', fields={
        'verification_required': drf_serializers.BooleanField(),
        'session_token':         drf_serializers.CharField(),
    })},
)
class ResendVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email    = request.data.get('email', '').lower().strip()
        password = request.data.get('password', '')

        if not email or not password:
            return Response({'detail': 'email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email__iexact=email, is_active=False).first()
        if not user or not user.check_password(password):
            return Response(
                {'detail': 'No unverified account found with those credentials.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        otp = _create_otp(user, EmailOTP.Purpose.EMAIL_VERIFICATION)
        _send_otp_email(user, otp.code, EmailOTP.Purpose.EMAIL_VERIFICATION)

        session_token = signing.dumps(str(user.id), salt='email-verify')
        return Response({'verification_required': True, 'session_token': session_token})


# ── Password Reset ────────────────────────────────────────────────────────────

@extend_schema(
    tags=['auth'],
    summary='Request a password reset OTP (sent via email)',
    request=inline_serializer('PasswordResetRequest', fields={'email': drf_serializers.EmailField()}),
    responses={200: inline_serializer('PasswordResetResponse', fields={'detail': drf_serializers.CharField()})},
)
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').lower().strip()
        user  = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            otp = _create_otp(user, EmailOTP.Purpose.PASSWORD_RESET)
            _send_otp_email(user, otp.code, EmailOTP.Purpose.PASSWORD_RESET)
        # Always 200 — never reveal whether the email is registered
        return Response({'detail': 'If that email is registered, a reset code has been sent.'})


@extend_schema(
    tags=['auth'],
    summary='Confirm password reset with OTP code',
    request=inline_serializer('PasswordResetConfirmRequest', fields={
        'email':        drf_serializers.EmailField(),
        'otp':          drf_serializers.CharField(),
        'new_password': drf_serializers.CharField(),
    }),
    responses={200: inline_serializer('PasswordResetConfirmResponse', fields={'detail': drf_serializers.CharField()})},
)
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email    = request.data.get('email', '').lower().strip()
        code     = request.data.get('otp', '').strip()
        new_pass = request.data.get('new_password', '')

        if not email or not code or not new_pass:
            return Response({'detail': 'email, otp, and new_password are required.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_pass) < 8:
            return Response({'detail': 'Password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            return Response({'detail': 'Invalid code.'}, status=status.HTTP_400_BAD_REQUEST)

        otp = (
            EmailOTP.objects
            .filter(user=user, purpose=EmailOTP.Purpose.PASSWORD_RESET, used_at__isnull=True)
            .order_by('-created_at')
            .first()
        )

        if otp is None or timezone.now() > otp.expires_at:
            return Response({'detail': 'Invalid or expired code.'}, status=status.HTTP_400_BAD_REQUEST)
        if otp.attempts >= 5:
            return Response({'detail': 'Too many failed attempts. Please request a new code.'}, status=status.HTTP_400_BAD_REQUEST)

        if otp.code != code:
            otp.attempts += 1
            otp.save(update_fields=['attempts'])
            return Response({'detail': 'Invalid code.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            otp.used_at = timezone.now()
            otp.save(update_fields=['used_at'])
            user.set_password(new_pass)
            user.save(update_fields=['password'])
            # Blacklist all outstanding refresh tokens for this user
            try:
                from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
                for t in OutstandingToken.objects.filter(user=user):
                    try:
                        RefreshToken(t.token).blacklist()
                    except Exception:
                        pass
            except Exception:
                pass

        return Response({'detail': 'Password reset successful. Please log in with your new password.'})


def get_user_org(request):
    return getattr(request.user, 'organisation', None)


def _issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


# ── Auth / onboarding views ───────────────────────────────────────────────────

@extend_schema(
    tags=['auth'],
    summary='Current user profile',
    responses={200: inline_serializer('MeResponse', fields={
        'id':           drf_serializers.UUIDField(),
        'email':        drf_serializers.EmailField(),
        'name':         drf_serializers.CharField(),
        'is_org_admin': drf_serializers.BooleanField(),
        'organisation': inline_serializer('MeOrg', fields={
            'id':   drf_serializers.UUIDField(),
            'name': drf_serializers.CharField(),
            'slug': drf_serializers.CharField(),
            'plan': drf_serializers.CharField(),
        }, allow_null=True),
    })},
)
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        org = get_user_org(request)
        return Response({
            'id':           user.id,
            'email':        user.email,
            'name':         f'{user.first_name} {user.last_name}'.strip() or user.username,
            'is_org_admin': user.is_org_admin,
            'organisation': {
                'id':   org.id,
                'name': org.name,
                'slug': org.slug,
                'plan': org.plan,
            } if org else None,
        })


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
            # is_active=False until email is verified via OTP
            user = User.objects.create_user(
                username=data['email'],
                email=data['email'],
                password=data['password'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                organisation=org,
                is_org_admin=True,
                is_active=False,
            )
            Person.objects.create(
                organisation=org,
                user=user,
                name=f"{data['first_name']} {data['last_name']}".strip(),
                email=data['email'],
            )

        otp = _create_otp(user, EmailOTP.Purpose.EMAIL_VERIFICATION)
        _send_otp_email(user, otp.code, EmailOTP.Purpose.EMAIL_VERIFICATION)

        session_token = signing.dumps(str(user.id), salt='email-verify')
        return Response(
            {'verification_required': True, 'session_token': session_token},
            status=status.HTTP_201_CREATED,
        )


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

        with transaction.atomic():
            user = User.objects.create_user(
                username=invite.email,
                email=invite.email,
                password=data['password'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                organisation=org,
                is_org_admin=False,
            )
            Person.objects.create(
                organisation=org,
                user=user,
                name=f"{data['first_name']} {data['last_name']}".strip(),
                email=invite.email,
            )
            invite.accepted_at = timezone.now()
            invite.save(update_fields=['accepted_at'])

        return Response(_issue_tokens(user), status=status.HTTP_201_CREATED)


# ── Person ViewSet ────────────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(tags=['persons'], summary='List org participants'),
    create=extend_schema(tags=['persons'], summary='Add a new person to the org'),
    retrieve=extend_schema(tags=['persons'], summary='Person detail + delivery stats + lineage'),
    partial_update=extend_schema(tags=['persons'], summary='Update person name, email, or role'),
    timeline=extend_schema(tags=['persons'], summary='Chronological meetings + commitments for a person'),
    topics=extend_schema(tags=['persons'], summary='Tag frequency list for a person'),
    link_slack=extend_schema(tags=['persons'], summary='Link a Slack user ID to this person'),
    merge=extend_schema(
        tags=['persons'],
        summary='Merge duplicate persons into one — reassigns all commitments, meetings, and events',
        request=MergePersonsSerializer,
        responses={200: PersonSerializer},
    ),
)
class PersonViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'post', 'head', 'options']

    def get_queryset(self):
        org = get_user_org(self.request)
        if org is None:
            return Person.objects.none()
        return Person.objects.filter(organisation=org).order_by('name')

    def perform_create(self, serializer):
        org = get_user_org(self.request)
        if org is None:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('User has no organisation.')
        serializer.save(organisation=org)

    @action(detail=False, methods=['post'])
    def merge(self, request):
        org = get_user_org(request)
        if org is None:
            return Response({'detail': 'User has no organisation.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = MergePersonsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            primary = Person.objects.get(pk=data['primary_id'], organisation=org)
        except Person.DoesNotExist:
            return Response({'detail': 'primary_id not found.'}, status=status.HTTP_404_NOT_FOUND)

        duplicates = list(Person.objects.filter(pk__in=data['duplicate_ids'], organisation=org))
        if len(duplicates) != len(data['duplicate_ids']):
            return Response({'detail': 'One or more duplicate_ids not found.'}, status=status.HTTP_404_NOT_FOUND)

        from django.db import transaction
        from apps.meetings.models import MeetingParticipant
        from apps.commitments.models import Commitment, EscalationEvent, ExtractionFeedback, CommitmentEvent

        with transaction.atomic():
            for dup in duplicates:
                # Transfer User link if primary has none
                if dup.user_id and not primary.user_id:
                    primary.user = dup.user
                    dup.user = None
                    dup.save(update_fields=['user'])

                # Reassign commitments
                Commitment.objects.filter(owner=dup).update(owner=primary)
                Commitment.objects.filter(reviewed_by=dup).update(reviewed_by=primary)

                # Reassign escalation events
                EscalationEvent.objects.filter(escalated_by=dup).update(escalated_by=primary)
                EscalationEvent.objects.filter(escalated_to=dup).update(escalated_to=primary)

                # Reassign extraction feedback and audit events
                ExtractionFeedback.objects.filter(given_by=dup).update(given_by=primary)
                CommitmentEvent.objects.filter(actor=dup).update(actor=primary)

                # Reassign meeting participants — skip if primary already in that meeting
                existing_meeting_ids = set(
                    MeetingParticipant.objects.filter(person=primary).values_list('meeting_id', flat=True)
                )
                for mp in MeetingParticipant.objects.filter(person=dup):
                    if mp.meeting_id in existing_meeting_ids:
                        mp.delete()
                    else:
                        mp.person = primary
                        mp.save(update_fields=['person'])

                dup.delete()

            # Recompute meeting_count
            primary.meeting_count = MeetingParticipant.objects.filter(person=primary).count()
            primary.save()

        return Response(PersonSerializer(primary).data)

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

def _create_otp(user, purpose):
    """Invalidate previous unused OTPs for this purpose, then create a fresh one."""
    EmailOTP.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(used_at=timezone.now())
    code = f"{secrets.randbelow(1_000_000):06d}"
    return EmailOTP.objects.create(
        user=user,
        code=code,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=10),
    )


def _send_otp_email(user, code, purpose):
    subjects = {
        EmailOTP.Purpose.EMAIL_VERIFICATION: 'Verify your Verato email address',
        EmailOTP.Purpose.PASSWORD_RESET:     'Reset your Verato password',
    }
    bodies = {
        EmailOTP.Purpose.EMAIL_VERIFICATION: (
            f"Hi {user.first_name or user.email},\n\n"
            f"Welcome to Verato! Your email verification code is:\n\n    {code}\n\n"
            f"This code expires in 10 minutes. Do not share it with anyone.\n\n"
            f"If you didn't create a Verato account, please ignore this email."
        ),
        EmailOTP.Purpose.PASSWORD_RESET: (
            f"Hi {user.first_name or user.email},\n\n"
            f"Your Verato password reset code is:\n\n    {code}\n\n"
            f"This code expires in 10 minutes. Do not share it with anyone.\n\n"
            f"If you didn't request a password reset, please ignore this email."
        ),
    }
    try:
        send_mail(
            subject=subjects.get(purpose, 'Your Verato code'),
            message=bodies.get(purpose, f"Your code is: {code}"),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("Failed to send OTP email to %s: %s", user.email, exc)
        raise


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
