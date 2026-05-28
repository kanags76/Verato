from django.db.models import Count, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins, filters, status
from rest_framework.decorators import action, api_view, permission_classes as drf_permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Commitment, CommitmentEvent, CommitmentTag, EscalationEvent, ExtractionFeedback
from .serializers import CommitmentSerializer, CommitmentEventSerializer, ResolveSerializer, CommitmentTagDetailSerializer
from apps.accounts.models import MeetingManager
from apps.accounts.views import get_user_org
from apps.meetings.models import Meeting
from apps.notifications.models import InAppNotification


def _serialize_commitment(commitment, request=None):
    """Re-fetch with prefetches so action responses include freshly-written related objects."""
    fresh = (
        Commitment.objects
        .select_related('owner', 'meeting__created_by')
        .prefetch_related('tags', 'escalations')
        .get(pk=commitment.pk)
    )
    context = {'request': request} if request else {}
    return CommitmentSerializer(fresh, context=context).data


def _get_actor(request):
    """Return the Person linked to the logged-in user, or None."""
    return getattr(request.user, 'person', None)


def _log(commitment, event_type, actor, old_value=None, new_value=None, note=''):
    CommitmentEvent.objects.create(
        commitment=commitment,
        event_type=event_type,
        actor=actor,
        old_value=old_value,
        new_value=new_value,
        note=note,
    )


def _has_cos_access(user, meeting):
    """True if user is the meeting owner, an accepted delegate, or an org admin."""
    if user.is_org_admin:
        return True
    if not meeting.created_by_id:
        return user.is_org_admin
    if meeting.created_by_id == user.pk:
        return True
    return MeetingManager.objects.filter(
        manager_user=user,
        managed_user_id=meeting.created_by_id,
        status=MeetingManager.Status.ACCEPTED,
    ).exists()


def _notify_cos_of_owner_update(commitment, actor):
    """Alert the meeting's CoS when an action owner (not CoS) logs an update."""
    cos_user = commitment.meeting.created_by
    if not cos_user:
        return
    if actor and getattr(actor, 'user_id', None) == cos_user.pk:
        return
    if actor and actor.user_id:
        is_delegate = MeetingManager.objects.filter(
            manager_user_id=actor.user_id,
            managed_user=cos_user,
            status=MeetingManager.Status.ACCEPTED,
        ).exists()
        if is_delegate:
            return
    actor_name = actor.name if actor else 'Someone'
    InAppNotification.objects.create(
        organisation=commitment.organisation,
        commitment=commitment,
        notification_type=InAppNotification.Type.OWNER_UPDATE,
        message=f'{actor_name} logged an update on: {commitment.normalised_text[:100]}',
        recipient_user=cos_user,
    )


@extend_schema_view(
    list=extend_schema(
        tags=['commitments'],
        summary='List commitments',
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR,
                description='Filter by status: pending_review | active | at_risk | escalated | done | deferred | cancelled'),
            OpenApiParameter('owner', OpenApiTypes.UUID, description='Filter by owner person ID'),
            OpenApiParameter('source', OpenApiTypes.STR, description='Filter by source: transcript | import'),
            OpenApiParameter('tags__label', OpenApiTypes.STR, description='Filter by tag label'),
            OpenApiParameter('priority', OpenApiTypes.STR, description='Filter by priority: high | medium | low'),
            OpenApiParameter('deadline_before', OpenApiTypes.DATE, description='Commitments due before this date (YYYY-MM-DD)'),
            OpenApiParameter('risk_gte', OpenApiTypes.FLOAT, description='Minimum risk score (0.0–1.0)'),
        ],
    ),
    retrieve=extend_schema(tags=['commitments'], summary='Commitment detail with escalation history'),
    partial_update=extend_schema(tags=['commitments'], summary='Update owner or deadline'),
    confirm=extend_schema(tags=['commitments'], summary='Confirm extraction: PENDING_REVIEW → ACTIVE'),
    reject=extend_schema(tags=['commitments'], summary='Reject extraction: discard + log feedback'),
    escalate=extend_schema(tags=['commitments'], summary='Manually escalate commitment'),
    resolve=extend_schema(tags=['commitments'], summary='Resolve commitment: done | deferred | cancelled'),
    bulk_confirm=extend_schema(
        tags=['commitments'],
        summary='Bulk confirm all pending commitments (optionally filter by min_confidence)',
    ),
    nudge=extend_schema(
        tags=['commitments'],
        summary='Send or log a nudge to the commitment owner',
        description=(
            'method: slack (default) | email | phone | in_person | other. '
            'For slack, sends a DM if owner has slack_user_id. '
            'All methods log a NUDGED event in history.'
        ),
    ),
    log_update=extend_schema(
        tags=['commitments'],
        summary='Log owner response after a manual nudge',
        description=(
            'Record what the owner said after the CoS followed up. '
            'Body: { "response": "...", "new_status": "active|deferred|done|cancelled" (optional) }. '
            'Creates a FIELD_EDITED event in history.'
        ),
    ),
    reopen=extend_schema(tags=['commitments'], summary='Reopen a closed commitment → ACTIVE'),
    history=extend_schema(tags=['commitments'], summary='Unified audit timeline: escalations + feedback events, newest first'),
)
class CommitmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CommitmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'source', 'owner', 'meeting', 'tags__label', 'priority']
    ordering_fields = ['deadline', 'risk_score', 'created_at']
    ordering = ['deadline', '-risk_score']
    http_method_names = ['get', 'patch', 'post', 'head', 'options']

    def get_queryset(self):
        org  = get_user_org(self.request)
        user = self.request.user
        if org is None:
            return Commitment.objects.none()

        if user.is_org_admin:
            qs = Commitment.objects.filter(organisation=org)
        else:
            delegated_from = MeetingManager.objects.filter(
                manager_user=user, status=MeetingManager.Status.ACCEPTED,
            ).values_list('managed_user_id', flat=True)
            cos_meeting_ids = Meeting.objects.filter(
                organisation=org,
            ).filter(
                Q(created_by=user) | Q(created_by_id__in=delegated_from)
            ).values_list('id', flat=True)

            actor = getattr(user, 'person', None)
            if actor:
                qs = Commitment.objects.filter(organisation=org).filter(
                    Q(meeting_id__in=cos_meeting_ids) | Q(owner=actor)
                )
            else:
                qs = Commitment.objects.filter(organisation=org, meeting_id__in=cos_meeting_ids)

        qs = qs.select_related('owner', 'meeting__created_by').prefetch_related('tags', 'escalations')

        deadline_before = self.request.query_params.get('deadline_before')
        if deadline_before:
            qs = qs.filter(deadline__lte=deadline_before)

        risk_gte = self.request.query_params.get('risk_gte')
        if risk_gte:
            try:
                qs = qs.filter(risk_score__gte=float(risk_gte))
            except ValueError:
                pass

        return qs

    def partial_update(self, request, *args, **kwargs):
        commitment = self.get_object()
        actor = _get_actor(request)

        old_vals = {
            'normalised_text': commitment.normalised_text,
            'priority':        commitment.priority,
            'owner':           commitment.owner.name if commitment.owner else None,
            'deadline':        str(commitment.deadline) if commitment.deadline else None,
            'tags':            list(commitment.tags.values_list('label', flat=True)),
        }

        response = super().partial_update(request, *args, **kwargs)

        commitment.refresh_from_db()
        new_vals = {
            'normalised_text': commitment.normalised_text,
            'priority':        commitment.priority,
            'owner':           commitment.owner.name if commitment.owner else None,
            'deadline':        str(commitment.deadline) if commitment.deadline else None,
            'tags':            list(commitment.tags.values_list('label', flat=True)),
        }

        changed_old = {k: old_vals[k] for k in old_vals if old_vals[k] != new_vals[k]}
        changed_new = {k: new_vals[k] for k in changed_old}
        if changed_old:
            _log(commitment, CommitmentEvent.EventType.FIELD_EDITED, actor,
                 old_value=changed_old, new_value=changed_new)

        return response

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        commitment = self.get_object()
        if not _has_cos_access(request.user, commitment.meeting):
            return Response(
                {'detail': 'Only the meeting owner or a delegate can confirm commitments.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if commitment.status != Commitment.Status.PENDING_REVIEW:
            return Response(
                {'detail': f'Cannot confirm a commitment with status {commitment.status!r}.'},
                status=status.HTTP_409_CONFLICT,
            )
        commitment.status = Commitment.Status.ACTIVE
        commitment.reviewed_at = timezone.now()
        commitment.save(update_fields=['status', 'reviewed_at', 'updated_at'])

        ExtractionFeedback.objects.create(
            commitment=commitment,
            organisation=commitment.organisation,
            feedback_type=ExtractionFeedback.FeedbackType.CONFIRMED,
            from_import=(commitment.source == Commitment.Source.IMPORT),
        )
        _log(commitment, CommitmentEvent.EventType.CONFIRMED, _get_actor(request),
             new_value={'status': 'active'})
        return Response(_serialize_commitment(commitment, request))

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        commitment = self.get_object()
        if not _has_cos_access(request.user, commitment.meeting):
            return Response(
                {'detail': 'Only the meeting owner or a delegate can reject commitments.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if commitment.status != Commitment.Status.PENDING_REVIEW:
            return Response(
                {'detail': f'Cannot reject a commitment with status {commitment.status!r}.'},
                status=status.HTTP_409_CONFLICT,
            )
        ExtractionFeedback.objects.create(
            commitment=commitment,
            organisation=commitment.organisation,
            feedback_type=ExtractionFeedback.FeedbackType.REJECTED,
            note=request.data.get('note', ''),
            from_import=(commitment.source == Commitment.Source.IMPORT),
        )
        commitment.status = Commitment.Status.CANCELLED
        commitment.save(update_fields=['status', 'updated_at'])
        _log(commitment, CommitmentEvent.EventType.REJECTED, _get_actor(request),
             new_value={'status': 'cancelled'},
             note=request.data.get('note', ''))
        return Response(_serialize_commitment(commitment, request))

    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        commitment = self.get_object()
        if not _has_cos_access(request.user, commitment.meeting):
            return Response(
                {'detail': 'Only the meeting owner or a delegate can escalate commitments.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        closed = {Commitment.Status.DELIVERED, Commitment.Status.CANCELLED}
        if commitment.status in closed:
            return Response(
                {'detail': 'Cannot escalate a closed commitment.'},
                status=status.HTTP_409_CONFLICT,
            )
        commitment.status = Commitment.Status.ESCALATED
        commitment.save(update_fields=['status', 'updated_at'])

        EscalationEvent.objects.create(
            commitment=commitment,
            method=EscalationEvent.Method.MANUAL,
            message_sent=request.data.get('message', ''),
        )
        _log(commitment, CommitmentEvent.EventType.ESCALATED, _get_actor(request),
             new_value={'status': 'escalated'},
             note=request.data.get('message', ''))
        return Response(_serialize_commitment(commitment, request))

    @action(detail=False, methods=['post'], url_path='bulk-confirm')
    def bulk_confirm(self, request):
        """Confirm all PENDING_REVIEW commitments in accessible meetings."""
        org = get_user_org(request)
        if org is None:
            return Response({'detail': 'User has no organisation.'}, status=status.HTTP_403_FORBIDDEN)

        qs = self.get_queryset().filter(status=Commitment.Status.PENDING_REVIEW)

        meeting_id = request.data.get('meeting')
        if meeting_id:
            qs = qs.filter(meeting_id=meeting_id)

        min_confidence = request.data.get('min_confidence')
        if min_confidence is not None:
            try:
                qs = qs.filter(confidence__gte=float(min_confidence))
            except (ValueError, TypeError):
                return Response({'detail': 'min_confidence must be a float.'}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        ids = list(qs.values_list('id', flat=True))
        count = qs.update(status=Commitment.Status.ACTIVE, reviewed_at=now)

        ExtractionFeedback.objects.bulk_create([
            ExtractionFeedback(
                commitment_id=pk,
                organisation=org,
                feedback_type=ExtractionFeedback.FeedbackType.CONFIRMED,
                from_import=False,
            )
            for pk in ids
        ])

        return Response({'confirmed': count})

    @action(detail=True, methods=['post'])
    def nudge(self, request, pk=None):
        commitment = self.get_object()
        if not commitment.owner:
            return Response({'detail': 'Commitment has no owner.'}, status=status.HTTP_400_BAD_REQUEST)

        method = request.data.get('method', 'slack')
        note   = request.data.get('note', '').strip()
        owner  = commitment.owner
        channel = None

        if method == 'slack':
            if not owner.slack_user_id:
                return Response(
                    {'detail': 'Owner has no Slack user ID. Use method: email | phone | in_person | other.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            from apps.notifications.slack import send_nudge_dm
            channel = send_nudge_dm(owner.slack_user_id, commitment)
            if channel is None:
                return Response(
                    {'detail': 'Slack is not configured or message could not be sent.'},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        elif method == 'email':
            from apps.notifications.gmail import send_nudge_email
            from apps.notifications.models import NudgeLog
            org = commitment.organisation
            to_email = getattr(owner, 'email', '') or ''
            if not to_email:
                return Response(
                    {'detail': 'Owner has no email address.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            thread_id = send_nudge_email(org, to_email, owner.name, commitment, note=note)
            if thread_id is None:
                return Response(
                    {'detail': 'Gmail is not connected or email could not be sent.'},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            # Store thread_id on a NudgeLog so poll_gmail_replies can track the reply.
            # get_or_create ensures idempotency; update sets the thread_id.
            nl, _ = NudgeLog.objects.get_or_create(
                commitment=commitment,
                nudge_type=NudgeLog.NudgeType.FIRST_REMINDER,
                defaults={'person': owner, 'channel': ''},
            )
            if thread_id:
                nl.gmail_thread_id = thread_id
                nl.save(update_fields=['gmail_thread_id'])

        method_label = {
            'slack':      'Slack DM',
            'email':      'Email',
            'phone':      'Phone call',
            'in_person':  'In person',
            'other':      'Other',
        }.get(method, method)

        log_note = f'Nudge via {method_label} to {owner.name}'
        if note:
            log_note += f' — {note}'

        _log(commitment, CommitmentEvent.EventType.NUDGED, _get_actor(request), note=log_note)
        return Response({'detail': 'Nudge logged.', 'method': method, 'channel': channel})

    @action(detail=True, methods=['post'], url_path='log-update')
    def log_update(self, request, pk=None):
        commitment    = self.get_object()
        response_text = (request.data.get('response') or '').strip()
        new_status    = (request.data.get('new_status') or '').strip()

        if not response_text:
            return Response({'detail': 'response is required.'}, status=status.HTTP_400_BAD_REQUEST)

        old_status = commitment.status
        if new_status:
            # Only CoS / delegate / org admin can change status — action owners log text only.
            if not _has_cos_access(request.user, commitment.meeting):
                return Response(
                    {'detail': 'Only the meeting owner or a delegate can change commitment status.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            valid_statuses = {
                'active':    Commitment.Status.ACTIVE,
                'deferred':  Commitment.Status.DEFERRED,
                'done':      Commitment.Status.DELIVERED,
                'cancelled': Commitment.Status.CANCELLED,
            }
            if new_status not in valid_statuses:
                return Response(
                    {'detail': f'new_status must be one of: {", ".join(valid_statuses)}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            commitment.status = valid_statuses[new_status]
            if commitment.status in {Commitment.Status.DELIVERED, Commitment.Status.CANCELLED}:
                commitment.resolved_at     = timezone.now()
                commitment.resolution_note = response_text
                commitment.save(update_fields=['status', 'resolved_at', 'resolution_note', 'updated_at'])
            else:
                commitment.save(update_fields=['status', 'updated_at'])

        actor = _get_actor(request)
        _log(
            commitment,
            CommitmentEvent.EventType.FIELD_EDITED,
            actor,
            old_value={'status': old_status} if new_status else None,
            new_value={'status': commitment.status} if new_status else None,
            note=f'Owner update: {response_text}',
        )
        _notify_cos_of_owner_update(commitment, actor)
        return Response({
            'detail':   'Update logged.',
            'status':   commitment.status,
            'response': response_text,
        })

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        commitment = self.get_object()
        if not _has_cos_access(request.user, commitment.meeting):
            return Response(
                {'detail': 'Only the meeting owner or a delegate can resolve commitments.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        closed = {
            Commitment.Status.DELIVERED,
            Commitment.Status.CANCELLED,
            Commitment.Status.DEFERRED,
        }
        if commitment.status in closed:
            return Response(
                {'detail': 'Commitment is already closed.'},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = ResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        outcome_map = {
            'done':      Commitment.Status.DELIVERED,
            'deferred':  Commitment.Status.DEFERRED,
            'cancelled': Commitment.Status.CANCELLED,
        }
        commitment.status          = outcome_map[data['outcome']]
        commitment.resolved_at     = timezone.now()
        commitment.resolution_note = data.get('note', '')

        update_fields = ['status', 'resolved_at', 'resolution_note', 'updated_at']
        new_deadline = data.get('new_deadline')
        if new_deadline:
            commitment.deadline = new_deadline
            update_fields.append('deadline')

        commitment.save(update_fields=update_fields)
        _log(commitment, CommitmentEvent.EventType.RESOLVED, _get_actor(request),
             new_value={
                 'status':   commitment.status,
                 'deadline': str(new_deadline) if new_deadline else None,
             },
             note=data.get('note', ''))

        # Notify action owner when CoS resolves or defers
        if data['outcome'] in {'done', 'deferred'}:
            owner_user = getattr(getattr(commitment, 'owner', None), 'user', None)
            if owner_user:
                outcome_label = 'marked as Done' if data['outcome'] == 'done' else 'deferred'
                InAppNotification.objects.create(
                    organisation=commitment.organisation,
                    commitment=commitment,
                    notification_type=InAppNotification.Type.COMMITMENT_CLOSED,
                    message=f'Your action "{commitment.normalised_text[:100]}" has been {outcome_label}.',
                    recipient_user=owner_user,
                )

        return Response(_serialize_commitment(commitment, request))

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        commitment = self.get_object()
        if not _has_cos_access(request.user, commitment.meeting):
            return Response(
                {'detail': 'Only the meeting owner or a delegate can reopen commitments.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        reopenable = {
            Commitment.Status.DELIVERED,
            Commitment.Status.CANCELLED,
            Commitment.Status.DEFERRED,
        }
        if commitment.status not in reopenable:
            return Response(
                {'detail': f'Cannot reopen a commitment with status {commitment.status!r}.'},
                status=status.HTTP_409_CONFLICT,
            )
        commitment.status      = Commitment.Status.ACTIVE
        commitment.resolved_at = None
        commitment.save(update_fields=['status', 'resolved_at', 'updated_at'])
        _log(commitment, CommitmentEvent.EventType.REOPENED, _get_actor(request),
             new_value={'status': 'active'})
        return Response(_serialize_commitment(commitment, request))

    @action(detail=True, methods=['post'], url_path='auto-tag')
    def auto_tag(self, request, pk=None):
        """Use Gemini to suggest and apply tags for this commitment."""
        commitment = self.get_object()
        if not _has_cos_access(request.user, commitment.meeting):
            return Response({'detail': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)

        org = commitment.organisation
        existing_labels = list(
            CommitmentTag.objects.filter(organisation=org)
            .values_list('label', flat=True)
            .order_by('label')
        )

        from extraction.extractor import _call_gemini
        existing_str = ', '.join(existing_labels) if existing_labels else '(none yet)'
        prompt = (
            f'You are a tagging assistant for an executive commitment tracker.\n\n'
            f'Commitment: "{commitment.normalised_text}"\n\n'
            f'Existing tags in this organisation: {existing_str}\n\n'
            f'Return a JSON array of 1-4 lowercase tag labels that best categorise this commitment. '
            f'Reuse existing tags where appropriate. Only create a new tag if the commitment clearly '
            f'belongs to a theme not covered by existing tags. Keep labels short (1-3 words). '
            f'Return ONLY the JSON array, nothing else. Example: ["product", "q2 roadmap"]'
        )
        raw = _call_gemini(prompt)
        if not raw:
            return Response({'detail': 'AI tagging unavailable right now.'}, status=status.HTTP_502_BAD_GATEWAY)

        import json
        try:
            raw = raw.strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
            suggested = json.loads(raw)
            if not isinstance(suggested, list):
                raise ValueError('not a list')
            suggested = [str(s).lower().strip() for s in suggested if str(s).strip()][:4]
        except (json.JSONDecodeError, ValueError):
            return Response({'detail': 'Could not parse AI response.', 'raw': raw}, status=status.HTTP_502_BAD_GATEWAY)

        for label in suggested:
            tag, _ = CommitmentTag.objects.get_or_create(organisation=org, label=label)
            commitment.tags.add(tag)

        _log(commitment, CommitmentEvent.EventType.FIELD_EDITED, _get_actor(request),
             note=f'Auto-tagged: {", ".join(suggested)}')
        return Response({'applied_tags': suggested, **_serialize_commitment(commitment, request)})

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        commitment = self.get_object()
        user       = request.user
        actor      = _get_actor(request)
        is_cos     = _has_cos_access(user, commitment.meeting)

        events = []

        if is_cos:
            event_qs     = commitment.events.select_related('actor').order_by('occurred_at')
            escalation_qs = commitment.escalations.select_related('escalated_by', 'escalated_to').order_by('occurred_at')
        else:
            # Action owners only see events they authored themselves
            event_qs = (
                commitment.events.filter(actor=actor)
                .select_related('actor')
                .order_by('occurred_at')
            ) if actor else commitment.events.none()
            escalation_qs = commitment.escalations.none()

        for ev in event_qs:
            events.append({
                'type':        'event',
                'event_type':  ev.event_type,
                'label':       ev.get_event_type_display(),
                'actor':       ev.actor.name if ev.actor else None,
                'old_value':   ev.old_value,
                'new_value':   ev.new_value,
                'note':        ev.note,
                'occurred_at': ev.occurred_at,
            })

        for esc in escalation_qs:
            events.append({
                'type':        'escalation',
                'event_type':  esc.method,
                'label':       f'Escalated via {esc.get_method_display()}',
                'actor':       esc.escalated_by.name if esc.escalated_by else None,
                'target':      esc.escalated_to.name if esc.escalated_to else None,
                'message':     esc.message_sent,
                'outcome':     esc.outcome,
                'occurred_at': esc.occurred_at,
            })

        events.sort(key=lambda e: e['occurred_at'], reverse=True)
        return Response(events)


# ── Tags ──────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=['tags'],
    summary='Tag autocomplete — list org tags ranked by usage, optionally filtered by prefix',
    parameters=[OpenApiParameter('q', OpenApiTypes.STR, description='Prefix filter for tag label')],
)
@api_view(['GET'])
@drf_permission_classes([IsAuthenticated])
def tag_list(request):
    org = get_user_org(request)
    if org is None:
        return Response([])

    qs = (
        CommitmentTag.objects
        .filter(organisation=org)
        .annotate(usage=Count('commitments'))
        .order_by('-usage', 'label')
    )

    q = request.query_params.get('q', '').strip()
    if q:
        qs = qs.filter(label__istartswith=q)

    return Response(CommitmentTagDetailSerializer(qs, many=True).data)


class CommitmentTagViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD management for org tags (rename, promote to initiative, delete, merge)."""
    serializer_class = CommitmentTagDetailSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'delete', 'post', 'head', 'options']

    def get_queryset(self):
        org = get_user_org(self.request)
        if org is None:
            return CommitmentTag.objects.none()
        return (
            CommitmentTag.objects
            .filter(organisation=org)
            .annotate(usage=Count('commitments'))
        )

    def _require_admin(self):
        if not self.request.user.is_org_admin:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only org admins can manage tags.')

    def partial_update(self, request, *args, **kwargs):
        self._require_admin()
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._require_admin()
        tag = self.get_object()
        label = tag.label
        tag.delete()
        return Response({'detail': f'Tag "{label}" deleted.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def merge(self, request, pk=None):
        """Merge this tag into another: all commitments re-tagged, this tag deleted."""
        self._require_admin()
        source_tag = self.get_object()
        target_label = (request.data.get('into') or '').strip().lower()
        if not target_label:
            return Response({'detail': '"into" (target tag label) is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if target_label == source_tag.label:
            return Response({'detail': 'Source and target tags must be different.'}, status=status.HTTP_400_BAD_REQUEST)

        org = get_user_org(request)
        target_tag, _ = CommitmentTag.objects.get_or_create(organisation=org, label=target_label)

        affected_commitments = source_tag.commitments.all()
        for c in affected_commitments:
            c.tags.add(target_tag)
            c.tags.remove(source_tag)

        count = affected_commitments.count()
        source_tag.delete()
        return Response({
            'detail': f'Merged "{source_tag.label}" into "{target_label}".',
            'commitments_updated': count,
        })

    @action(detail=True, methods=['post'], url_path='generate-summary')
    def generate_summary(self, request, pk=None):
        """Trigger Gemini to regenerate the AI summary for this initiative tag."""
        self._require_admin()
        tag = self.get_object()
        if not tag.is_initiative:
            return Response({'detail': 'Only initiative tags can have an AI summary.'}, status=status.HTTP_400_BAD_REQUEST)

        commitments = list(
            tag.commitments
            .exclude(status__in=['done', 'cancelled'])
            .select_related('owner')
            .values('normalised_text', 'status', 'deadline', 'owner__name')
        )

        if not commitments:
            return Response({'detail': 'No active commitments under this initiative.'}, status=status.HTTP_400_BAD_REQUEST)

        lines = []
        for c in commitments:
            owner = c['owner__name'] or 'Unassigned'
            deadline = str(c['deadline']) if c['deadline'] else 'no deadline'
            lines.append(f'- [{c["status"]}] {c["normalised_text"]} (Owner: {owner}, Due: {deadline})')

        from extraction.extractor import _call_gemini
        prompt = (
            f'You are summarising the status of a strategic initiative called "{tag.label}" '
            f'for a Chief of Staff.\n\n'
            f'Initiative description: {tag.description or "(none)"}\n\n'
            f'Active commitments under this initiative:\n' + '\n'.join(lines) + '\n\n'
            f'Write a 2-3 sentence summary covering: overall health (on track / at risk / blocked), '
            f'key upcoming deadlines, and any red flags. Be direct and factual. No fluff.'
        )
        summary = _call_gemini(prompt)
        if not summary:
            return Response({'detail': 'AI summary generation failed.'}, status=status.HTTP_502_BAD_GATEWAY)

        from django.utils import timezone as tz
        tag.ai_summary = summary.strip()
        tag.ai_summary_at = tz.now()
        tag.save(update_fields=['ai_summary', 'ai_summary_at'])

        qs = CommitmentTag.objects.filter(pk=tag.pk).annotate(usage=Count('commitments'))
        return Response(CommitmentTagDetailSerializer(qs.first()).data)


# ── Initiatives list ──────────────────────────────────────────────────────────

@extend_schema(
    tags=['initiatives'],
    summary='List strategic initiatives with commitment counts by status',
)
@api_view(['GET'])
@drf_permission_classes([IsAuthenticated])
def initiatives_list(request):
    org = get_user_org(request)
    if org is None:
        return Response([])

    tags = (
        CommitmentTag.objects
        .filter(organisation=org, is_initiative=True)
        .annotate(
            total=Count('commitments'),
            active=Count('commitments', filter=Q(commitments__status='active')),
            at_risk=Count('commitments', filter=Q(commitments__status='at_risk')),
            escalated=Count('commitments', filter=Q(commitments__status='escalated')),
            done=Count('commitments', filter=Q(commitments__status='done')),
            pending=Count('commitments', filter=Q(commitments__status='pending_review')),
        )
        .order_by('label')
    )

    data = []
    for tag in tags:
        data.append({
            'id':           str(tag.id),
            'label':        tag.label,
            'description':  tag.description,
            'ai_summary':   tag.ai_summary,
            'ai_summary_at': tag.ai_summary_at,
            'counts': {
                'total':     tag.total,
                'active':    tag.active,
                'at_risk':   tag.at_risk,
                'escalated': tag.escalated,
                'done':      tag.done,
                'pending':   tag.pending,
            },
        })

    return Response(data)
