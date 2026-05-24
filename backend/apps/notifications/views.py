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


# ── Gmail OAuth ───────────────────────────────────────────────────────────────

_GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid',
]


@extend_schema(tags=['gmail'], summary='Gmail connection status')
@api_view(['GET'])
@drf_permission_classes([IsAuthenticated])
def gmail_status(request):
    org = getattr(request.user, 'organisation', None)
    if org is None:
        return Response({'connected': False, 'email': None})
    s = org.settings or {}
    return Response({
        'connected': bool(s.get('gmail_refresh_token')),
        'email':     s.get('gmail_email'),
    })


def gmail_oauth_start(request):
    """Redirect browser to Google OAuth consent for Gmail access."""
    from rest_framework_simplejwt.tokens import AccessToken
    from rest_framework_simplejwt.exceptions import TokenError
    from apps.accounts.models import User

    token_str = request.GET.get('auth', '')
    if token_str:
        try:
            token = AccessToken(token_str)
            user  = User.objects.get(pk=token['user_id'])
            request.user = user
        except (TokenError, User.DoesNotExist):
            return HttpResponse('Invalid or expired token.', status=401)
    elif not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)

    org = getattr(request.user, 'organisation', None)
    if org is None:
        return HttpResponse('User has no organisation.', status=403)

    from urllib.parse import urlencode
    state = signing.dumps({'org_id': str(org.id)}, salt='gmail-oauth')
    params = urlencode({
        'client_id':     settings.GOOGLE_CLIENT_ID,
        'redirect_uri':  settings.GOOGLE_GMAIL_REDIRECT_URI,
        'response_type': 'code',
        'scope':         ' '.join(_GMAIL_SCOPES),
        'access_type':   'offline',
        'prompt':        'consent',
        'state':         state,
    })
    return HttpResponseRedirect(f'https://accounts.google.com/o/oauth2/v2/auth?{params}')


@csrf_exempt
def gmail_oauth_callback(request):
    """Exchange Google auth code for tokens and store on org."""
    if request.GET.get('error'):
        return _close_window_response('Gmail connection cancelled.')

    code  = request.GET.get('code', '')
    state = request.GET.get('state', '')
    if not code or not state:
        return _close_window_response('Missing code or state.', error=True)

    try:
        data   = signing.loads(state, salt='gmail-oauth', max_age=3600)
        org_id = data['org_id']
    except signing.BadSignature:
        return _close_window_response('Invalid state parameter.', error=True)

    try:
        from apps.accounts.models import Organisation
        org = Organisation.objects.get(id=org_id)
    except Organisation.DoesNotExist:
        return _close_window_response('Organisation not found.', error=True)

    try:
        import requests as http_requests
        token_resp = http_requests.post('https://oauth2.googleapis.com/token', data={
            'code':          code,
            'client_id':     settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'redirect_uri':  settings.GOOGLE_GMAIL_REDIRECT_URI,
            'grant_type':    'authorization_code',
        })
        token_resp.raise_for_status()
        tokens = token_resp.json()

        # Get the user's email
        userinfo_resp = http_requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f"Bearer {tokens['access_token']}"},
        )
        gmail_email = userinfo_resp.json().get('email', '')

    except Exception as exc:
        logger.error("Gmail OAuth token exchange failed: %s", exc)
        return _close_window_response('Gmail connection failed. Please try again.', error=True)

    s = org.settings or {}
    s['gmail_access_token']  = tokens.get('access_token')
    s['gmail_refresh_token'] = tokens.get('refresh_token')
    s['gmail_email']         = gmail_email
    org.settings = s
    org.save(update_fields=['settings'])

    logger.info("Gmail connected for org %s (%s)", org.slug, gmail_email)
    return _close_window_response(f'Gmail connected — {gmail_email} ✓')


# ── Nudge settings ────────────────────────────────────────────────────────────

_VALID_FIRST_DAYS   = {1, 2, 5}
_VALID_SECOND_HOURS = {24, 48, 72}


@extend_schema(
    tags=['slack'],
    summary='Get or update org nudge timing settings',
    description=(
        'GET: returns current nudge schedule settings. '
        'PATCH: update first_days_before (1/2/5) and/or second_hours_before (24/48/72).'
    ),
)
@api_view(['GET', 'PATCH'])
@drf_permission_classes([IsAuthenticated])
def nudge_settings(request):
    org = getattr(request.user, 'organisation', None)
    if org is None:
        return Response({'detail': 'User has no organisation.'}, status=403)

    if request.method == 'PATCH':
        data = request.data
        org_settings = org.settings or {}

        if 'nudge_enabled' in data:
            org_settings['nudge_enabled'] = bool(data['nudge_enabled'])

        if 'first_days_before' in data:
            val = int(data['first_days_before'])
            if val not in _VALID_FIRST_DAYS:
                return Response(
                    {'detail': f'first_days_before must be one of {sorted(_VALID_FIRST_DAYS)}.'},
                    status=400,
                )
            org_settings['nudge_first_days_before'] = val

        if 'second_hours_before' in data:
            val = int(data['second_hours_before'])
            if val not in _VALID_SECOND_HOURS:
                return Response(
                    {'detail': f'second_hours_before must be one of {sorted(_VALID_SECOND_HOURS)}.'},
                    status=400,
                )
            org_settings['nudge_second_hours_before'] = val

        org.settings = org_settings
        org.save(update_fields=['settings'])

    org_settings = org.settings or {}
    return Response({
        'nudge_enabled':       org_settings.get('nudge_enabled', False),
        'first_days_before':   org_settings.get('nudge_first_days_before', 2),
        'second_hours_before': org_settings.get('nudge_second_hours_before', 48),
        'post_due_days':       [1, 2, 3],
        'escalate_cos_on_overdue': True,
    })


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


@extend_schema(tags=['slack'], summary='Disconnect Slack — removes org bot token')
@api_view(['POST'])
@drf_permission_classes([IsAuthenticated])
def slack_disconnect(request):
    org = getattr(request.user, 'organisation', None)
    if org is None:
        return Response({'detail': 'User has no organisation.'}, status=403)
    s = org.settings or {}
    s.pop('slack_token', None)
    s.pop('slack_workspace_id', None)
    s.pop('slack_workspace_name', None)
    org.settings = s
    org.save(update_fields=['settings'])
    return Response({'detail': 'Slack disconnected.'})


@extend_schema(tags=['gmail'], summary='Disconnect Gmail — removes org OAuth tokens')
@api_view(['POST'])
@drf_permission_classes([IsAuthenticated])
def gmail_disconnect(request):
    org = getattr(request.user, 'organisation', None)
    if org is None:
        return Response({'detail': 'User has no organisation.'}, status=403)
    s = org.settings or {}
    s.pop('gmail_access_token', None)
    s.pop('gmail_refresh_token', None)
    s.pop('gmail_email', None)
    org.settings = s
    org.save(update_fields=['settings'])
    return Response({'detail': 'Gmail disconnected.'})


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
        owner = getattr(commitment, 'owner', None)
        name  = owner.name if owner else 'Owner'
        create_cos_notification(
            commitment.organisation, commitment,
            f'{name} marked "{commitment.normalised_text[:80]}" as Done via Slack.',
            'slack_reply',
        )


def _handle_delayed(commitment):
    if commitment.status not in {Commitment.Status.DELIVERED, Commitment.Status.CANCELLED}:
        commitment.status = Commitment.Status.DEFERRED
        commitment.save(update_fields=['status', 'updated_at'])
        logger.info("Slack nudge: commitment %s marked DEFERRED", commitment.id)
        owner = getattr(commitment, 'owner', None)
        name  = owner.name if owner else 'Owner'
        create_cos_notification(
            commitment.organisation, commitment,
            f'{name} needs more time on "{commitment.normalised_text[:80]}" (Slack).',
            'slack_reply',
        )


def _handle_blocked(commitment):
    if commitment.status not in {Commitment.Status.DELIVERED, Commitment.Status.CANCELLED}:
        commitment.status = Commitment.Status.AT_RISK
        commitment.save(update_fields=['status', 'updated_at'])
        logger.info("Slack nudge: commitment %s marked AT_RISK (blocked)", commitment.id)
        owner = getattr(commitment, 'owner', None)
        name  = owner.name if owner else 'Owner'
        create_cos_notification(
            commitment.organisation, commitment,
            f'{name} is blocked on "{commitment.normalised_text[:80]}" (Slack).',
            'slack_reply',
        )


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
    summary='Import selected Slack users as Persons',
    description=(
        'Send a list of slack_user_ids. For each: fetches their Slack profile, '
        'then checks if a Person with that email already exists in the org — '
        'if yes, links the slack_user_id to that Person; '
        'if no, creates a new Person from their Slack profile. '
        'Returns each person with an "action" field: "linked" or "created".'
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

    slack_ids = request.data.get('slack_user_ids', [])
    if not slack_ids:
        return Response({'detail': 'Provide a non-empty slack_user_ids list.'}, status=400)

    results = []
    for slack_id in slack_ids:
        slack_id = slack_id.strip()
        if not slack_id:
            continue

        # Fetch Slack profile
        try:
            resp    = client.users_info(user=slack_id)
            member  = resp['user']
            profile = member.get('profile', {})
            name    = profile.get('real_name') or profile.get('display_name') or slack_id
            email   = (profile.get('email') or '').strip().lower() or None
        except Exception as exc:
            logger.error("slack_users_import: users_info failed for %s: %s", slack_id, exc)
            return Response({'detail': f'Slack API error fetching {slack_id}: {exc}'}, status=502)

        # Email match → link; no match → create
        person = Person.objects.filter(organisation=org, email__iexact=email).first() if email else None

        if person:
            person.slack_user_id = slack_id
            person.save(update_fields=['slack_user_id'])
            action = 'linked'
        else:
            person, created = Person.objects.get_or_create(
                organisation=org,
                slack_user_id=slack_id,
                defaults={'name': name, 'email': email},
            )
            if not created and not person.email and email:
                person.email = email
                person.save(update_fields=['email'])
            action = 'created'

        data = PersonSerializer(person, context={'request': request}).data
        data['action'] = action
        results.append(data)

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
        data   = signing.loads(state, salt='slack-oauth', max_age=3600)
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


# ── In-app notifications ──────────────────────────────────────────────────────

def create_cos_notification(org, commitment, message, notification_type):
    """
    Create an InAppNotification for all org admin users.
    Called from Slack action handlers and Gmail poll task.
    """
    from .models import InAppNotification
    InAppNotification.objects.create(
        organisation=org,
        commitment=commitment,
        message=message,
        notification_type=notification_type,
    )


@extend_schema(tags=['notifications'], summary='List in-app notifications for current user')
@api_view(['GET'])
@drf_permission_classes([IsAuthenticated])
def notification_list(request):
    from .models import InAppNotification
    org = getattr(request.user, 'organisation', None)
    if org is None:
        return Response([])
    qs = InAppNotification.objects.filter(organisation=org).order_by('-created_at')[:50]
    data = [
        {
            'id':                str(n.id),
            'message':           n.message,
            'notification_type': n.notification_type,
            'is_read':           n.is_read,
            'created_at':        n.created_at.isoformat(),
            'commitment_id':     str(n.commitment_id) if n.commitment_id else None,
        }
        for n in qs
    ]
    return Response(data)


@extend_schema(tags=['notifications'], summary='Unread notification count')
@api_view(['GET'])
@drf_permission_classes([IsAuthenticated])
def notification_unread_count(request):
    from .models import InAppNotification
    org = getattr(request.user, 'organisation', None)
    if org is None:
        return Response({'unread': 0})
    count = InAppNotification.objects.filter(organisation=org, is_read=False).count()
    return Response({'unread': count})


@extend_schema(tags=['notifications'], summary='Mark a notification as read')
@api_view(['POST'])
@drf_permission_classes([IsAuthenticated])
def notification_mark_read(request, pk):
    from .models import InAppNotification
    org = getattr(request.user, 'organisation', None)
    try:
        n = InAppNotification.objects.get(pk=pk, organisation=org)
    except InAppNotification.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)
    n.is_read = True
    n.save(update_fields=['is_read'])
    return Response({'detail': 'Marked as read.'})


@extend_schema(tags=['notifications'], summary='Mark all notifications as read')
@api_view(['POST'])
@drf_permission_classes([IsAuthenticated])
def notification_mark_all_read(request):
    from .models import InAppNotification
    org = getattr(request.user, 'organisation', None)
    if org is None:
        return Response({'detail': 'No organisation.'}, status=400)
    InAppNotification.objects.filter(organisation=org, is_read=False).update(is_read=True)
    return Response({'detail': 'All marked as read.'})


# ── Google Calendar OAuth ─────────────────────────────────────────────────────

_CALENDAR_SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
]


@extend_schema(tags=['calendar'], summary='Google Calendar connection status')
@api_view(['GET'])
@drf_permission_classes([IsAuthenticated])
def calendar_status(request):
    from .models import CalendarConnection
    org = getattr(request.user, 'organisation', None)
    try:
        conn = CalendarConnection.objects.get(organisation=org)
        return Response({
            'connected':             True,
            'email':                 conn.calendar_email,
            'last_synced_at':        conn.last_synced_at.isoformat() if conn.last_synced_at else None,
            'transcripts_detected':  conn.transcripts_detected,
            'transcripts_supported': conn.transcripts_detected,  # None = unknown, True = yes, False = no
        })
    except CalendarConnection.DoesNotExist:
        return Response({'connected': False, 'transcripts_supported': None})


@extend_schema(tags=['calendar'], summary='Start Google Calendar OAuth flow')
@require_GET
def calendar_oauth_start(request):
    from google_auth_oauthlib.flow import Flow
    token = request.GET.get('auth', '')
    if not token:
        return HttpResponse('Missing auth token.', status=400)

    state = signing.dumps({'jwt': token}, salt='calendar-oauth')
    flow = Flow.from_client_config(
        {
            'web': {
                'client_id':                   settings.GOOGLE_CLIENT_ID,
                'client_secret':               settings.GOOGLE_CLIENT_SECRET,
                'auth_uri':                    'https://accounts.google.com/o/oauth2/auth',
                'token_uri':                   'https://oauth2.googleapis.com/token',
                'redirect_uris':               [settings.GOOGLE_CALENDAR_REDIRECT_URI],
            }
        },
        scopes=_CALENDAR_SCOPES,
    )
    flow.redirect_uri = settings.GOOGLE_CALENDAR_REDIRECT_URI
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='false',
        prompt='consent',
        state=state,
    )
    return HttpResponseRedirect(auth_url)


@extend_schema(tags=['calendar'], summary='Google Calendar OAuth callback')
@require_GET
@csrf_exempt
def calendar_oauth_callback(request):
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from .models import CalendarConnection

    code  = request.GET.get('code', '')
    state = request.GET.get('state', '')
    if not code or not state:
        return _close_window_response('Missing code or state.', error=True)

    try:
        data = signing.loads(state, salt='calendar-oauth', max_age=3600)
        jwt_token = data['jwt']
    except signing.BadSignature:
        return _close_window_response('Invalid state parameter.', error=True)

    # Resolve org from JWT
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        token_obj = AccessToken(jwt_token)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=token_obj['user_id'])
        org  = user.organisation
        if org is None:
            return _close_window_response('User has no organisation.', error=True)
    except Exception as exc:
        logger.error("Calendar OAuth JWT resolve failed: %s", exc)
        return _close_window_response('Authentication error. Please try again.', error=True)

    # Exchange code for tokens
    try:
        import os
        os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'  # Google adds openid to returned scopes
        flow = Flow.from_client_config(
            {
                'web': {
                    'client_id':     settings.GOOGLE_CLIENT_ID,
                    'client_secret': settings.GOOGLE_CLIENT_SECRET,
                    'auth_uri':      'https://accounts.google.com/o/oauth2/auth',
                    'token_uri':     'https://oauth2.googleapis.com/token',
                    'redirect_uris': [settings.GOOGLE_CALENDAR_REDIRECT_URI],
                }
            },
            scopes=_CALENDAR_SCOPES,
            state=state,
        )
        flow.redirect_uri = settings.GOOGLE_CALENDAR_REDIRECT_URI
        flow.fetch_token(code=code)
        creds = flow.credentials
    except Exception as exc:
        logger.error("Calendar OAuth token exchange failed: %s", exc)
        return _close_window_response('Failed to connect Google Calendar. Please try again.', error=True)

    # Get calendar email
    try:
        service = build('oauth2', 'v2', credentials=creds, cache_discovery=False)
        info    = service.userinfo().get().execute()
        cal_email = info.get('email', '')
    except Exception:
        cal_email = ''

    # Probe Drive to detect if workspace supports Meet transcripts
    transcripts_detected = _probe_meet_transcripts(creds)

    # Save / update connection
    CalendarConnection.objects.update_or_create(
        organisation=org,
        defaults={
            'access_token':        creds.token,
            'refresh_token':       creds.refresh_token or '',
            'token_expiry':        creds.expiry,
            'calendar_email':      cal_email,
            'transcripts_detected': transcripts_detected,
        },
    )
    logger.info("Google Calendar connected for org %s (%s) — transcripts_detected=%s", org.slug, cal_email, transcripts_detected)
    return _close_window_response('Google Calendar connected successfully! ✓')


def _probe_meet_transcripts(creds):
    """
    Search Drive for any Google Meet transcript files created in the last 90 days.
    Returns True if found, False if not, None if the search itself failed.
    """
    try:
        from googleapiclient.discovery import build
        from django.utils import timezone
        from datetime import timedelta

        drive = build('drive', 'v3', credentials=creds, cache_discovery=False)
        cutoff = (timezone.now() - timedelta(days=90)).isoformat()
        results = drive.files().list(
            q=f"name contains 'Transcript' and mimeType='application/vnd.google-apps.document' and createdTime > '{cutoff}'",
            fields='files(id,name,createdTime)',
            pageSize=1,
        ).execute()
        found = len(results.get('files', [])) > 0
        return found
    except Exception as exc:
        logger.warning("Drive transcript probe failed: %s", exc)
        return None


@extend_schema(tags=['calendar'], summary='Disconnect Google Calendar')
@api_view(['POST'])
@drf_permission_classes([IsAuthenticated])
def calendar_disconnect(request):
    from .models import CalendarConnection
    org = getattr(request.user, 'organisation', None)
    CalendarConnection.objects.filter(organisation=org).delete()
    return Response({'detail': 'Google Calendar disconnected.'})
