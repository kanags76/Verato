from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AcceptInviteView,
    InvitationListView,
    InviteView,
    LogoutView,
    MeView,
    OrgSettingsView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PersonViewSet,
    RegisterView,
    ValidateInviteView,
    VerifyOTPView,
)

router = DefaultRouter()
router.register('persons', PersonViewSet, basename='person')

urlpatterns = [
    path('auth/me/',                        MeView.as_view(),                  name='me'),
    path('auth/logout/',                    LogoutView.as_view(),              name='logout'),
    path('auth/register/',                  RegisterView.as_view(),            name='register'),
    path('auth/invite/',                    InviteView.as_view(),              name='invite'),
    path('auth/invite/validate/',           ValidateInviteView.as_view(),      name='validate-invite'),
    path('auth/invite/accept/',             AcceptInviteView.as_view(),        name='accept-invite'),
    path('auth/invitations/',               InvitationListView.as_view(),      name='invitation-list'),
    path('auth/token/verify-otp/',          VerifyOTPView.as_view(),           name='verify-otp'),
    path('auth/password/reset/',            PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('auth/password/reset/confirm/',    PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('orgs/<uuid:pk>/settings/',        OrgSettingsView.as_view(),         name='org-settings'),
] + router.urls
