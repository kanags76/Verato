from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Person
from .serializers import PersonSerializer


def get_user_org(request):
    """Return the organisation for the authenticated user, or None."""
    return getattr(request.user, 'organisation', None)


@extend_schema_view(
    list=extend_schema(tags=['persons'], summary='List org participants'),
    retrieve=extend_schema(tags=['persons'], summary='Person detail + delivery stats'),
)
class PersonViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org = get_user_org(self.request)
        if org is None:
            return Person.objects.none()
        return Person.objects.filter(organisation=org).order_by('name')
