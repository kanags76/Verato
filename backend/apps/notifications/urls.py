from django.urls import path
from .views import (
    nudge_settings,
    slack_actions,
    slack_oauth_callback,
    slack_oauth_start,
    slack_status,
    slack_test_message,
    slack_users_search,
    slack_users_import,
    slack_users_sync,
)

urlpatterns = [
    path('nudge-settings/',       nudge_settings,      name='nudge-settings'),
    path('slack/actions/',        slack_actions,        name='slack-actions'),
    path('slack/oauth/start/',    slack_oauth_start,    name='slack-oauth-start'),
    path('slack/oauth/callback/', slack_oauth_callback, name='slack-oauth-callback'),
    path('slack/status/',         slack_status,         name='slack-status'),
    path('slack/test-message/',   slack_test_message,   name='slack-test-message'),
    path('slack/users/',          slack_users_search,   name='slack-users-search'),
    path('slack/users/import/',   slack_users_import,   name='slack-users-import'),
    path('slack/users/sync/',     slack_users_sync,     name='slack-users-sync'),
]
