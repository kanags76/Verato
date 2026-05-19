from django.urls import path
from .views import (
    slack_actions,
    slack_oauth_callback,
    slack_oauth_start,
    slack_status,
    slack_test_message,
)

urlpatterns = [
    path('slack/actions/',        slack_actions,       name='slack-actions'),
    path('slack/oauth/start/',    slack_oauth_start,   name='slack-oauth-start'),
    path('slack/oauth/callback/', slack_oauth_callback,name='slack-oauth-callback'),
    path('slack/status/',         slack_status,        name='slack-status'),
    path('slack/test-message/',   slack_test_message,  name='slack-test-message'),
]
