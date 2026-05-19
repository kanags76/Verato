from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CommitmentViewSet, tag_list

router = DefaultRouter()
router.register('commitments', CommitmentViewSet, basename='commitment')

urlpatterns = router.urls + [
    path('tags/', tag_list, name='tag-list'),
]
