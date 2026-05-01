from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins, filters
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Commitment
from .serializers import CommitmentSerializer
from apps.accounts.views import get_user_org


@extend_schema_view(
    list=extend_schema(
        tags=['commitments'],
        summary='List commitments',
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR,
                description='Filter by status: pending_review | active | at_risk | escalated | delivered | deferred | cancelled'),
            OpenApiParameter('owner', OpenApiTypes.UUID, description='Filter by owner person ID'),
            OpenApiParameter('source', OpenApiTypes.STR, description='Filter by source: transcript | import'),
            OpenApiParameter('deadline_before', OpenApiTypes.DATE, description='Commitments due before this date (YYYY-MM-DD)'),
            OpenApiParameter('risk_gte', OpenApiTypes.FLOAT, description='Minimum risk score (0.0–1.0)'),
        ],
    ),
    retrieve=extend_schema(tags=['commitments'], summary='Commitment detail'),
    partial_update=extend_schema(tags=['commitments'], summary='Update owner or deadline'),
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
    filterset_fields = ['status', 'source', 'owner']
    ordering_fields = ['deadline', 'risk_score', 'created_at']
    ordering = ['deadline', '-risk_score']
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        org = get_user_org(self.request)
        if org is None:
            return Commitment.objects.none()

        qs = Commitment.objects.filter(organisation=org).select_related('owner', 'meeting')

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
