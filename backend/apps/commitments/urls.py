from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CommitmentViewSet, CommitmentTagViewSet, tag_list, initiatives_list

router = DefaultRouter()
router.register('commitments', CommitmentViewSet, basename='commitment')
router.register('tags', CommitmentTagViewSet, basename='tag')

urlpatterns = router.urls + [
    path('tags/search/', tag_list, name='tag-list'),
    path('initiatives/', initiatives_list, name='initiatives-list'),
]
