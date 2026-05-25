from datetime import date

from django.db.models import Count, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.accounts.models import MeetingManager
from apps.accounts.views import get_user_org
from apps.commitments.models import Commitment
from apps.meetings.models import Meeting


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['dashboard'],
        summary='CoS command-centre summary stats',
        responses={200: {
            'type': 'object',
            'properties': {
                'overdue':      {'type': 'integer'},
                'at_risk':      {'type': 'integer'},
                'on_track':     {'type': 'integer'},
                'total_active': {'type': 'integer'},
            },
        }},
    )
    def get(self, request):
        org  = get_user_org(request)
        user = request.user
        if org is None:
            return Response({'overdue': 0, 'at_risk': 0, 'on_track': 0, 'total_active': 0})

        today = date.today()
        active_statuses = [
            Commitment.Status.ACTIVE,
            Commitment.Status.AT_RISK,
            Commitment.Status.ESCALATED,
            Commitment.Status.PENDING_REVIEW,
        ]

        if user.is_org_admin:
            base_qs = Commitment.objects.filter(organisation=org, status__in=active_statuses)
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
                base_qs = Commitment.objects.filter(
                    organisation=org, status__in=active_statuses,
                ).filter(Q(meeting_id__in=cos_meeting_ids) | Q(owner=actor))
            else:
                base_qs = Commitment.objects.filter(
                    organisation=org, status__in=active_statuses, meeting_id__in=cos_meeting_ids,
                )

        summary = base_qs.aggregate(
            overdue=Count('id', filter=Q(deadline__lt=today)),
            at_risk=Count('id', filter=Q(risk_score__gte=0.7, deadline__gte=today)),
            on_track=Count('id', filter=Q(risk_score__lt=0.7, deadline__gte=today) | Q(deadline__isnull=True)),
            total_active=Count('id'),
        )
        return Response(summary)
