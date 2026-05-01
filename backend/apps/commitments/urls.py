from rest_framework.routers import DefaultRouter
from .views import CommitmentViewSet

router = DefaultRouter()
router.register('commitments', CommitmentViewSet, basename='commitment')

urlpatterns = router.urls
