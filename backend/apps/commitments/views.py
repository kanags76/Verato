from django.db.models import Count
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
from .serializers import CommitmentSerializer, CommitmentEventSerializer, ResolveSerializer
from apps.accounts.views import get_user_org


def _serialize_commitment(commitment):
    """Re-fetch with prefetches so action responses include freshly-written related objects."""
    fresh = (
        Commitment.objects
        .select_related('owner', 'meeting')
        .prefetch_related('tags', 'escalations')
        .get(pk=commitment.pk)
    )
    return CommitmentSerializer(fresh).data


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
    nudge=extend_schema(tags=['commitments'], summary='Send a Slack deadline nudge to the commitment owner'),
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
        org = get_user_org(self.request)
        if org is None:
            return Commitment.objects.none()

        qs = (
            Commitment.objects
            .filter(organisation=org)
            .select_related('owner', 'meeting')
            .prefetch_related('tags', 'escalations')
        )

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
        return Response(_serialize_commitment(commitment))

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        commitment = self.get_object()
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
        return Response(_serialize_commitment(commitment))

    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        commitment = self.get_object()
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
        return Response(_serialize_commitment(commitment))

    @action(detail=False, methods=['post'], url_path='bulk-confirm')
    def bulk_confirm(self, request):
        """Confirm all PENDING_REVIEW commitments, optionally filtered by minimum confidence."""
        org = get_user_org(request)
        if org is None:
            return Response({'detail': 'User has no organisation.'}, status=status.HTTP_403_FORBIDDEN)

        qs = Commitment.objects.filter(organisation=org, status=Commitment.Status.PENDING_REVIEW)

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
        """Manually send a Slack deadline nudge DM to the commitment owner."""
        commitment = self.get_object()

        if not commitment.owner:
            return Response({'detail': 'Commitment has no owner.'}, status=status.HTTP_400_BAD_REQUEST)
        if not commitment.owner.slack_user_id:
            return Response(
                {'detail': 'Owner has no Slack user ID linked.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.notifications.slack import send_nudge_dm
        channel = send_nudge_dm(commitment.owner.slack_user_id, commitment)

        if channel is None:
            return Response(
                {'detail': 'Slack is not configured or the message could not be sent.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        _log(commitment, CommitmentEvent.EventType.NUDGED, _get_actor(request),
             note=f'Slack nudge sent to {commitment.owner.name}')
        return Response({'detail': 'Nudge sent.', 'channel': channel})

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        commitment = self.get_object()
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
        return Response(_serialize_commitment(commitment))

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        commitment = self.get_object()
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
        return Response(_serialize_commitment(commitment))

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        commitment = self.get_object()

        events = []

        # Primary audit log
        for ev in commitment.events.select_related('actor').order_by('occurred_at'):
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

        # Escalation events — include for detail (message text, outcome, target person)
        for esc in commitment.escalations.select_related('escalated_by', 'escalated_to').order_by('occurred_at'):
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


# ── Tag autocomplete ──────────────────────────────────────────────────────────

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

    return Response([{'label': t.label, 'usage': t.usage} for t in qs])
