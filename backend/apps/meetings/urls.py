from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MeetingViewSet, MeetingUploadView, MeetingImportView, MeetingStatusView

router = DefaultRouter()
router.register('meetings', MeetingViewSet, basename='meeting')

# Custom paths listed BEFORE router.urls so "upload" and "import" are not
# matched as <pk> by the router's meetings/<pk>/ pattern.
urlpatterns = [
    path('meetings/upload/', MeetingUploadView.as_view(),  name='meeting-upload'),
    path('meetings/import/', MeetingImportView.as_view(),  name='meeting-import'),
    path('meetings/<uuid:pk>/status/', MeetingStatusView.as_view(), name='meeting-status'),
] + router.urls
