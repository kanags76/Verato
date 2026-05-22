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


# ── Slack user management ─────────────────────────────────────────────────────

def _slack_user_to_dict(member, org):
    """Convert a Slack API member dict to a response dict with already_in_app flag."""
    from apps.accounts.models import Person
    profile    = member.get('profile', {})
    slack_id   = member['id']
    email      = profile.get('email', '')
    name       = profile.get('real_name') or profile.get('display_name') or slack_id
    avatar     = profile.get('image_48', '')

    person = (
        Person.objects.filter(organisation=org, slack_user_id=slack_id).first()
        or (Person.objects.filter(organisation=org, email__iexact=email).first() if email else None)
    )
    return {
        'slack_user_id': slack_id,
        'name':          name,
        'email':         email,
        'avatar':        avatar,
        'already_in_app': person is not None,
        'person_id':     str(person.id) if person else None,
    }


def _require_slack_client(org):
    """Return (client, None) or (None, error_response)."""
    from .slack import _get_client
    from rest_framework.response import Response
    client = _get_client(org=org)
    if client is None:
        return None, Response({'detail': 'Slack is not connected for this organisation.'}, status=400)
    return client, None


@extend_schema(
    tags=['slack'],
    summary='Search Slack workspace users',
    description=(
        'Search the connected Slack workspace by email (exact) or name (partial). '
        'Each result includes an already_in_app flag so the CoS knows who is already a Person.'
    ),
)
@api_view(['GET'])
@drf_permission_classes([IsAuthenticated])
def slack_users_search(request):
    org = getattr(request.user, 'organisation', None)
    if org is None:
        return Response({'detail': 'User has no organisation.'}, status=403)

    client, err = _require_slack_client(org)
    if err:
        return err

    q = request.query_params.get('q', '').strip()
    if not q:
        return Response({'detail': 'Provide a ?q= search term (email or name).'}, status=400)

    results = []
    try:
        if '@' in q:
            resp   = client.users_lookupByEmail(email=q)
            member = resp.get('user')
            if member and not member.get('deleted') and not member.get('is_bot'):
                results = [_slack_user_to_dict(member, org)]
        else:
            resp = client.users_list(limit=200)
            q_lower = q.lower()
            for member in resp.get('members', []):
                if member.get('deleted') or member.get('is_bot') or member.get('id') == 'USLACKBOT':
                    continue
                profile = member.get('profile', {})
                haystack = (
                    (profile.get('real_name') or '') + ' ' +
                    (profile.get('display_name') or '') + ' ' +
                    (profile.get('email') or '')
                ).lower()
                if q_lower in haystack:
                    results.append(_slack_user_to_dict(member, org))
    except Exception as exc:
        logger.error("slack_users_search: Slack API error: %s", exc)
        return Response({'detail': f'Slack API error: {exc}'}, status=502)

    return Response(results)


@extend_schema(
    tags=['slack'],
    summary='Import Slack users as Persons',
    description=(
        'For each selected Slack user: if person_id is provided, links slack_user_id to that Person. '
        'If no person_id, creates a new Person from the Slack profile.'
    ),
)
@api_view(['POST'])
@drf_permission_classes([IsAuthenticated])
def slack_users_import(request):
    from apps.accounts.models import Person
    from apps.accounts.serializers import PersonSerializer

    org = getattr(request.user, 'organisation', None)
    if org is None:
        return Response({'detail': 'User has no organisation.'}, status=403)

    client, err = _require_slack_client(org)
    if err:
        return err

    users = request.data.get('users', [])
    if not users:
        return Response({'detail': 'Provide a non-empty users list.'}, status=400)

    results = []
    for entry in users:
        slack_id  = entry.get('slack_user_id', '').strip()
        person_id = entry.get('person_id')
        if not slack_id:
            continue

        if person_id:
            try:
                person = Person.objects.get(id=person_id, organisation=org)
            except Person.DoesNotExist:
                return Response({'detail': f'Person {person_id} not found.'}, status=404)
            person.slack_user_id = slack_id
            person.save(update_fields=['slack_user_id'])
        else:
            try:
                resp    = client.users_info(user=slack_id)
                member  = resp['user']
                profile = member.get('profile', {})
                name    = profile.get('real_name') or profile.get('display_name') or slack_id
                email   = profile.get('email') or None
            except Exception as exc:
                logger.error("slack_users_import: users_info failed for %s: %s", slack_id, exc)
                return Response({'detail': f'Slack API error fetching {slack_id}: {exc}'}, status=502)

            person, _ = Person.objects.get_or_create(
                organisation=org,
                slack_user_id=slack_id,
                defaults={'name': name, 'email': email},
            )
            if not person.email and email:
                person.email = email
                person.save(update_fields=['email'])

        results.append(PersonSerializer(person, context={'request': request}).data)

    return Response(results, status=201)


@extend_schema(
    tags=['slack'],
    summary='Sync Slack workspace — get matches or confirm them',
    description=(
        'GET: pulls all Slack workspace members and auto-matches by email to existing Persons. '
        'Returns matched, unmatched_slack, and unmatched_persons lists. '
        'POST: body { "confirmations": [{ "person_id": "uuid", "slack_user_id": "U..." }] } '
        '— saves confirmed pairs. Can be called repeatedly.'
    ),
)
@api_view(['GET', 'POST'])
@drf_permission_classes([IsAuthenticated])
def slack_users_sync(request):
    from apps.accounts.models import Person
    from apps.accounts.serializers import PersonSerializer

    org = getattr(request.user, 'organisation', None)
    if org is None:
        return Response({'detail': 'User has no organisation.'}, status=403)

    client, err = _require_slack_client(org)
    if err:
        return err

    if request.method == 'POST':
        confirmations = request.data.get('confirmations', [])
        if not confirmations:
            return Response({'detail': 'Provide a non-empty confirmations list.'}, status=400)

        updated = 0
        for entry in confirmations:
            person_id = entry.get('person_id')
            slack_id  = entry.get('slack_user_id', '').strip()
            if not person_id or not slack_id:
                continue
            try:
                person = Person.objects.get(id=person_id, organisation=org)
            except Person.DoesNotExist:
                return Response({'detail': f'Person {person_id} not found.'}, status=404)
            person.slack_user_id = slack_id
            person.save(update_fields=['slack_user_id'])
            updated += 1

        return Response({'updated': updated})

    # GET — pull workspace and compute match lists
    try:
        resp    = client.users_list(limit=1000)
        members = resp.get('members', [])
    except Exception as exc:
        logger.error("slack_users_sync: users_list failed: %s", exc)
        return Response({'detail': f'Slack API error: {exc}'}, status=502)

    real_members = [
        m for m in members
        if not m.get('deleted') and not m.get('is_bot') and m.get('id') != 'USLACKBOT'
    ]

    persons     = list(Person.objects.filter(organisation=org))
    email_map   = {p.email.lower(): p for p in persons if p.email}
    slack_id_map = {p.slack_user_id: p for p in persons if p.slack_user_id}

    matched          = []
    unmatched_slack  = []
    matched_person_ids = set()

    for member in real_members:
        profile  = member.get('profile', {})
        slack_id = member['id']
        email    = profile.get('email', '')
        name     = profile.get('real_name') or profile.get('display_name') or slack_id
        avatar   = profile.get('image_48', '')

        if slack_id in slack_id_map:
            person = slack_id_map[slack_id]
            matched.append({
                'person':      PersonSerializer(person, context={'request': request}).data,
                'slack_user_id': slack_id,
                'slack_name':  name,
                'slack_email': email,
                'auto_matched': False,
                'already_linked': True,
            })
            matched_person_ids.add(person.id)
        elif email and email.lower() in email_map:
            person = email_map[email.lower()]
            matched.append({
                'person':      PersonSerializer(person, context={'request': request}).data,
                'slack_user_id': slack_id,
                'slack_name':  name,
                'slack_email': email,
                'auto_matched': True,
                'already_linked': False,
            })
            matched_person_ids.add(person.id)
        else:
            unmatched_slack.append({
                'slack_user_id': slack_id,
                'name':          name,
                'email':         email,
                'avatar':        avatar,
            })

    unmatched_persons = [
        {'id': str(p.id), 'name': p.name, 'email': p.email or ''}
        for p in persons
        if p.id not in matched_person_ids and not p.slack_user_id
    ]

    return Response({
        'matched':           matched,
        'unmatched_slack':   unmatched_slack,
        'unmatched_persons': unmatched_persons,
    })


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


def _close_window_response(message='', error=False):
    colour = '#ef4444' if error else '#10b981'
    html = f"""<!DOCTYPE html><html><head><title>Slack</title></head><body
        style="font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#0f172a;">
        <div style="text-align:center;color:#f1f5f9;">
            <p style="font-size:18px;color:{colour};">{message}</p>
            <p style="color:#94a3b8;font-size:14px;">You can close this window.</p>
        </div>
        <script>window.close();</script>
    </body></html>"""
    return HttpResponse(html)


@csrf_exempt
def slack_oauth_callback(request):
    """
    Slack redirects here after the user authorises the app.
    Exchange the code for a bot token and persist it on the org.
    """
    # User cancelled the Slack OAuth flow
    if request.GET.get('error'):
        return _close_window_response('Slack connection cancelled.')

    code  = request.GET.get('code', '')
    state = request.GET.get('state', '')

    if not code or not state:
        return _close_window_response('Missing code or state.', error=True)

    try:
        data   = signing.loads(state, salt='slack-oauth', max_age=600)
        org_id = data['org_id']
    except signing.BadSignature:
        return _close_window_response('Invalid state parameter.', error=True)

    try:
        from apps.accounts.models import Organisation
        org = Organisation.objects.get(id=org_id)
    except Organisation.DoesNotExist:
        return _close_window_response('Organisation not found.', error=True)

    client_id     = getattr(settings, 'SLACK_CLIENT_ID', '')
    client_secret = getattr(settings, 'SLACK_CLIENT_SECRET', '')
    redirect_uri  = getattr(settings, 'SLACK_OAUTH_REDIRECT_URI', '')

    if not client_id or not client_secret:
        return _close_window_response('Slack OAuth not configured.', error=True)

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
        return _close_window_response('Slack connection failed. Please try again.', error=True)

    org.settings['slack_token']          = token
    org.settings['slack_workspace_id']   = workspace_id
    org.settings['slack_workspace_name'] = workspace_name
    org.save(update_fields=['settings'])

    logger.info("Slack workspace %s connected to org %s", workspace_id, org.slug)
    return _close_window_response('Slack connected successfully! ✓')
