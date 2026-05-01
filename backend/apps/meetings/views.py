from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Meeting
from .serializers import MeetingSerializer
from apps.accounts.views import get_user_org


@extend_schema_view(
    list=extend_schema(tags=['meetings'], summary='List org meetings'),
    retrieve=extend_schema(tags=['meetings'], summary='Meeting detail'),
)
class MeetingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = MeetingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org = get_user_org(self.request)
        if org is None:
            return Meeting.objects.none()
        return Meeting.objects.filter(organisation=org).order_by('-occurred_at')
