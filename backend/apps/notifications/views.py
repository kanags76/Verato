"""
Slack action webhook — handles button clicks from nudge DMs.
Slack signs each request with SLACK_SIGNING_SECRET; we verify before processing.
"""
import json
import logging
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from rest_framework.decorators import api_view, permission_classes as drf_permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.commitments.models import Commitment

logger = logging.getLogger(__name__)


# ── Slack connection status ───────────────────────────────────────────────────

@extend_schema(
    tags=['slack'],
    summary='Slack connection status',
    description='Returns whether the org Slack workspace is connected and workspace metadata.',
    responses={200: {
        'type': 'object',
        'properties': {
            'connected':      {'type': 'boolean'},
            'workspace_id':   {'type': 'string', 'nullable': True},
            'workspace_name': {'type': 'string', 'nullable': True},
        },
    }},
)
@api_view(['GET'])
@drf_permission_classes([IsAuthenticated])
def slack_status(request):
    """Return whether the org's Slack workspace is connected and workspace info."""
    org = getattr(request.user, 'organisation', None)
    if org is None:
        return Response({'connected': False, 'workspace_id': None, 'workspace_name': None})

    org_settings = org.settings or {}
    token = org_settings.get('slack_token', '')
    return Response({
        'connected':      bool(token),
        'workspace_id':   org_settings.get('slack_workspace_id'),
        'workspace_name': org_settings.get('slack_workspace_name'),
    })


@extend_schema(
    tags=['slack'],
    summary='Send test Slack DM',
    description='Sends a test DM to the requesting user\'s linked Slack account. Requires slack_user_id set on the person.',
    responses={200: {'type': 'object', 'properties': {'detail': {'type': 'string'}}}},
)
@api_view(['POST'])
@drf_permission_classes([IsAuthenticated])
def slack_test_message(request):
    """Send a test DM to the requesting user's linked Slack account."""
    from .slack import _get_client

    org = getattr(request.user, 'organisation', None)
    if org is None:
        return Response({'detail': 'User has no organisation.'}, status=403)

    person = getattr(request.user, 'person', None)
    if person is None:
        return Response({'detail': 'No person record found for this user.'}, status=400)
    if not person.slack_user_id:
        return Response(
            {'detail': 'No Slack user ID linked. Use POST /persons/{id}/link-slack/ first.'},
            status=400,
        )

    client = _get_client(org=org)
    if client is None:
        return Response({'detail': 'Slack is not connected for this organisation.'}, status=400)

    try:
        client.chat_postMessage(
            channel=person.slack_user_id,
            text='Test message from Verato — your Slack integration is working correctly.',
        )
    except Exception as exc:
        logger.error("Slack test message failed for user %s: %s", request.user.id, exc)
        return Response({'detail': f'Slack message failed: {exc}'}, status=502)

    return Response({'detail': 'Test message sent.'})


def _verify_slack_signature(request) -> bool:
    """Verify the request came from Slack using the signing secret."""
    signing_secret = getattr(settings, 'SLACK_SIGNING_SECRET', '')
    if not signing_secret:
        return True  # skip verification in dev when secret not configured

    try:
        from slack_sdk.signature import SignatureVerifier
        verifier = SignatureVerifier(signing_secret)
        return verifier.is_valid_request(request.body, request.headers)
    except Exception:
        return False


@extend_schema(
    tags=['slack'],
    summary='Slack interactive button webhook',
    description='Receives Slack button-click payloads (Done / Need more time / Blocked) from nudge DMs. Called by Slack — not for direct use.',
    responses={200: None},
)
@csrf_exempt
@require_POST
def slack_actions(request):
    """
    Receives Slack interactive payloads (button clicks from nudge DMs).
    Transitions commitment status based on which button the owner pressed.
    """
    if not _verify_slack_signature(request):
        return HttpResponse(status=403)

    try:
        payload = json.loads(request.POST.get('payload', '{}'))
    except (json.JSONDecodeError, Exception):
        return HttpResponse(status=400)

    actions = payload.get('actions', [])
    if not actions:
        return HttpResponse(status=200)

    action    = actions[0]
    action_id = action.get('action_id', '')
    commit_id = action.get('value', '')

    try:
        commitment = Commitment.objects.get(id=commit_id)
    except (Commitment.DoesNotExist, Exception):
        logger.warning("Slack action: commitment %s not found", commit_id)
        return HttpResponse(status=200)

    if action_id == 'nudge_done':
        _handle_done(commitment)
    elif action_id == 'nudge_delayed':
        _handle_delayed(commitment)
    elif action_id == 'nudge_blocked':
        _handle_blocked(commitment)

    return HttpResponse(status=200)


def _handle_done(commitment):
    if commitment.status not in {Commitment.Status.DELIVERED, Commitment.Status.CANCELLED}:
        commitment.status      = Commitment.Status.DELIVERED
        commitment.resolved_at = timezone.now()
        commitment.save(update_fields=['status', 'resolved_at', 'updated_at'])
        logger.info("Slack nudge: commitment %s marked DELIVERED", commitment.id)


def _handle_delayed(commitment):
    if commitment.status not in {Commitment.Status.DELIVERED, Commitment.Status.CANCELLED}:
        commitment.status = Commitment.Status.DEFERRED
        commitment.save(update_fields=['status', 'updated_at'])
        logger.info("Slack nudge: commitment %s marked DEFERRED", commitment.id)


def _handle_blocked(commitment):
    if commitment.status not in {Commitment.Status.DELIVERED, Commitment.Status.CANCELLED}:
        commitment.status = Commitment.Status.AT_RISK
        commitment.save(update_fields=['status', 'updated_at'])
        logger.info("Slack nudge: commitment %s marked AT_RISK (blocked)", commitment.id)


# ── Slack OAuth ───────────────────────────────────────────────────────────────

@extend_schema(
    tags=['slack'],
    summary='Start Slack OAuth',
    description='Redirects the browser to Slack\'s OAuth consent screen. Open this URL directly in the browser after obtaining a JWT token.',
    responses={302: None},
)
def slack_oauth_start(request):
    """
    Redirect the authenticated user's browser to Slack's OAuth consent screen.
    Accepts JWT via ?auth= query param (for browser redirects where headers can't be set)
    or standard Authorization header.
    """
    from rest_framework_simplejwt.tokens import AccessToken
    from rest_framework_simplejwt.exceptions import TokenError
    from apps.accounts.models import User

    # ?auth=<jwt> takes priority over session cookies (browser flow)
    token_str = request.GET.get('auth', '')
    if token_str:
        try:
            token = AccessToken(token_str)
            user = User.objects.get(pk=token['user_id'])
            request.user = user
        except (TokenError, User.DoesNotExist):
            return HttpResponse('Invalid or expired token.', status=401)
    elif not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)

    org = getattr(request.user, 'organisation', None)
    if org is None:
        return HttpResponse('User has no organisation.', status=403)

    state = signing.dumps({'org_id': str(org.id)}, salt='slack-oauth')
    params = urlencode({
        'client_id':    settings.SLACK_CLIENT_ID,
        'scope':        'chat:write,im:write,users:read',
        'redirect_uri': settings.SLACK_OAUTH_REDIRECT_URI,
        'state':        state,
    })
    return HttpResponseRedirect(f'https://slack.com/oauth/v2/authorize?{params}')


@csrf_exempt
def slack_oauth_callback(request):
    """
    Slack redirects here after the user authorises the app.
    Exchange the code for a bot token and persist it on the org.
    """
    code  = request.GET.get('code', '')
    state = request.GET.get('state', '')

    if not code or not state:
        return HttpResponse('Missing code or state.', status=400)

    try:
        data   = signing.loads(state, salt='slack-oauth', max_age=600)
        org_id = data['org_id']
    except signing.BadSignature:
        return HttpResponse('Invalid state parameter.', status=400)

    try:
        from apps.accounts.models import Organisation
        org = Organisation.objects.get(id=org_id)
    except Organisation.DoesNotExist:
        return HttpResponse('Organisation not found.', status=404)

    client_id     = getattr(settings, 'SLACK_CLIENT_ID', '')
    client_secret = getattr(settings, 'SLACK_CLIENT_SECRET', '')
    redirect_uri  = getattr(settings, 'SLACK_OAUTH_REDIRECT_URI', '')

    if not client_id or not client_secret:
        return HttpResponse('Slack OAuth not configured.', status=503)

    try:
        from slack_sdk import WebClient
        client = WebClient()
        resp   = client.oauth_v2_access(
            client_id=client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=redirect_uri,
        )
        token          = resp['access_token']
        workspace_id   = resp['team']['id']
        workspace_name = resp['team']['name']
    except Exception as exc:
        logger.error("Slack OAuth callback failed: %s", exc)
        return HttpResponse('Slack OAuth failed. Please try again.', status=502)

    org.settings['slack_token']          = token
    org.settings['slack_workspace_id']   = workspace_id
    org.settings['slack_workspace_name'] = workspace_name
    org.save(update_fields=['settings'])

    logger.info("Slack workspace %s connected to org %s", workspace_id, org.slug)
    return HttpResponse('Slack connected! You can close this window.')
