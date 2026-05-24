import logging
from datetime import date

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from apps.commitments.models import Commitment, CommitmentEvent
from .models import NudgeLog, GmailPollLog
from .slack import send_nudge_dm, send_cos_overdue_alert

logger = logging.getLogger(__name__)

_SKIP_STATUSES = {Commitment.Status.DELIVERED, Commitment.Status.CANCELLED}


@shared_task
def send_deadline_nudges():
    """
    Daily nudge engine (runs 09:00 UTC via Celery Beat).

    Per org nudge schedule (configured via GET/PATCH /api/v1/nudge-settings/):
      - FIRST_REMINDER:  nudge_first_days_before days before deadline (default 2)
      - SECOND_REMINDER: nudge_second_hours_before / 24 days before deadline (default 48h)
      - OVERDUE_1/2/3:   1, 2, 3 days after deadline
      - ESCALATION:      CoS alerted on day +1

    Skip: no owner slack_user_id, DELIVERED/CANCELLED status, nudge_type already logged.
    """
    from apps.accounts.models import Organisation

    today = date.today()
    sent = escalated = skipped = 0

    for org in Organisation.objects.all():
        org_settings = org.settings or {}
        if not org_settings.get('slack_token'):
            continue
        if not org_settings.get('nudge_enabled', False):
            continue

        first_days   = int(org_settings.get('nudge_first_days_before', 2))
        second_hours = int(org_settings.get('nudge_second_hours_before', 48))
        second_days  = second_hours // 24
        cos_slack_id = _get_cos_slack_id(org)

        commitments = (
            Commitment.objects
            .filter(organisation=org, deadline__isnull=False)
            .exclude(status__in=_SKIP_STATUSES)
            .select_related('owner', 'organisation')
        )

        for commitment in commitments:
            days_until = (commitment.deadline - today).days  # negative when overdue
            days_over  = -days_until                          # positive when overdue

            due_types = _due_nudge_types(days_until, days_over, first_days, second_days, commitment)

            if not due_types:
                continue

            owner = commitment.owner
            if not owner or not owner.slack_user_id:
                skipped += 1
                continue

            for nudge_type in due_types:
                _, created = NudgeLog.objects.get_or_create(
                    commitment=commitment,
                    nudge_type=nudge_type,
                    defaults={'person': owner, 'channel': ''},
                )
                if not created:
                    continue  # already sent for this type

                channel = send_nudge_dm(owner.slack_user_id, commitment, nudge_type)
                if channel:
                    NudgeLog.objects.filter(
                        commitment=commitment, nudge_type=nudge_type
                    ).update(channel=channel)

                CommitmentEvent.objects.create(
                    commitment=commitment,
                    event_type=CommitmentEvent.EventType.NUDGED,
                    note=f'Slack nudge sent ({nudge_type}) to {owner.name}',
                )
                sent += 1

                # On first overdue day alert CoS (once per commitment)
                if nudge_type == NudgeLog.NudgeType.OVERDUE_1 and cos_slack_id:
                    _, cos_created = NudgeLog.objects.get_or_create(
                        commitment=commitment,
                        nudge_type=NudgeLog.NudgeType.ESCALATION,
                        defaults={'person': None, 'channel': ''},
                    )
                    if cos_created:
                        send_cos_overdue_alert(commitment, cos_slack_id)
                        escalated += 1

    logger.info(
        "send_deadline_nudges: %d nudges sent, %d CoS escalations, %d skipped (no Slack ID)",
        sent, escalated, skipped,
    )
    return {'sent': sent, 'escalated': escalated, 'skipped': skipped}


def _due_nudge_types(days_until, days_over, first_days, second_days, commitment):
    """Return list of NudgeType values due today for this commitment."""
    due = []

    if days_until == first_days:
        due.append(NudgeLog.NudgeType.FIRST_REMINDER)

    if days_until == second_days:
        if second_days != first_days:
            due.append(NudgeLog.NudgeType.SECOND_REMINDER)
        else:
            # Same day as FIRST — only add SECOND if FIRST already sent previously
            if NudgeLog.objects.filter(
                commitment=commitment, nudge_type=NudgeLog.NudgeType.FIRST_REMINDER
            ).exists():
                due.append(NudgeLog.NudgeType.SECOND_REMINDER)

    overdue_map = {1: NudgeLog.NudgeType.OVERDUE_1, 2: NudgeLog.NudgeType.OVERDUE_2, 3: NudgeLog.NudgeType.OVERDUE_3}
    if days_over in overdue_map:
        due.append(overdue_map[days_over])

    return due


def _get_cos_slack_id(org) -> str | None:
    from apps.accounts.models import User
    try:
        admin = (
            User.objects
            .filter(organisation=org, is_org_admin=True)
            .select_related('person')
            .first()
        )
        if admin and hasattr(admin, 'person') and admin.person.slack_user_id:
            return admin.person.slack_user_id
    except Exception:
        pass
    return None


@shared_task
def send_weekly_digest():
    """Monday 07:00 UTC — weekly commitment digest email."""
    from apps.accounts.models import User

    today = date.today()
    active_statuses = [
        Commitment.Status.ACTIVE,
        Commitment.Status.AT_RISK,
        Commitment.Status.ESCALATED,
        Commitment.Status.PENDING_REVIEW,
    ]

    orgs_sent = 0
    for org in _iter_orgs_with_email_users():
        commitments = list(
            Commitment.objects
            .filter(organisation=org, status__in=active_statuses)
            .select_related('owner')
            .order_by('deadline', '-risk_score')
        )
        if not commitments:
            continue

        overdue  = [c for c in commitments if c.deadline and c.deadline < today]
        at_risk  = [c for c in commitments if c.risk_score >= 0.7 and not (c.deadline and c.deadline < today)]
        on_track = [c for c in commitments if c.risk_score < 0.7 and not (c.deadline and c.deadline < today)]

        intro = _generate_digest_intro(org.name, overdue, at_risk, on_track)
        context = {'org_name': org.name, 'intro': intro, 'overdue': overdue,
                   'at_risk': at_risk, 'on_track': on_track, 'today': today}
        html_body = render_to_string('emails/weekly_digest.html', context)
        text_body = (
            f"Weekly digest for {org.name}\n\n{intro}\n\n"
            f"Overdue: {len(overdue)} | At risk: {len(at_risk)} | On track: {len(on_track)}"
        )

        recipients = list(
            User.objects.filter(organisation=org, email__gt='').values_list('email', flat=True)
        )
        if not recipients:
            continue

        msg = EmailMultiAlternatives(
            subject=f"Verato weekly digest — {today.strftime('%d %b %Y')}",
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        msg.attach_alternative(html_body, 'text/html')
        try:
            msg.send()
            orgs_sent += 1
        except Exception as exc:
            logger.error("Weekly digest failed for org %s: %s", org.slug, exc)

    logger.info("send_weekly_digest: sent for %d orgs", orgs_sent)
    return {'orgs_sent': orgs_sent}


def _iter_orgs_with_email_users():
    from apps.accounts.models import Organisation
    return Organisation.objects.filter(users__email__gt='').distinct()


def _generate_digest_intro(org_name, overdue, at_risk, on_track) -> str:
    try:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        prompt = (
            f"Write a 2-3 sentence executive summary for {org_name}'s weekly commitment digest. "
            f"{len(overdue)} overdue, {len(at_risk)} at-risk, {len(on_track)} on-track. "
            f"Be concise and action-oriented. Plain text only."
        )
        response = client.models.generate_content(
            model=settings.GEMINI_EXTRACTION_MODEL,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as exc:
        logger.warning("Gemini digest intro failed: %s", exc)
        return (
            f"Here is your weekly commitment summary for {org_name}. "
            f"{len(overdue)} overdue, {len(at_risk)} at risk, {len(on_track)} on track."
        )


@shared_task
def poll_gmail_replies():
    """
    Every 15 min — check Gmail reply threads for orgs with Gmail polling enabled.
    Per-org interval (gmail_poll_interval_minutes, default 30) is respected by
    comparing against the last GmailPollLog entry for that org.
    All runs logged to GmailPollLog.
    """
    from datetime import timedelta
    from django.utils import timezone
    from apps.accounts.models import Organisation
    from .gmail import poll_reply_threads, parse_reply_with_gemini

    total_updated = 0

    for org in Organisation.objects.all():
        s = org.settings or {}
        if not s.get('gmail_refresh_token'):
            continue
        if not s.get('gmail_polling_enabled', False):
            continue

        # Respect per-org poll interval
        interval_minutes = int(s.get('gmail_poll_interval_minutes', 30))
        last_poll = GmailPollLog.objects.filter(organisation=org).order_by('-polled_at').first()
        if last_poll:
            next_poll_due = last_poll.polled_at + timedelta(minutes=interval_minutes)
            if timezone.now() < next_poll_due - timedelta(seconds=60):
                continue

        poll_log = GmailPollLog(organisation=org)
        try:
            replies = poll_reply_threads(org)
            poll_log.threads_checked = len(replies)

            for reply in replies:
                nl         = reply['nudge_log']
                commitment = nl.commitment
                reply_body = reply['reply_body']

                if commitment.status in {Commitment.Status.DELIVERED, Commitment.Status.CANCELLED}:
                    continue

                deadline_str = commitment.deadline.strftime('%-d %b %Y') if commitment.deadline else 'none'
                parsed = parse_reply_with_gemini(commitment.normalised_text, deadline_str, reply_body)

                intent   = parsed.get('intent', 'no_update')
                note     = parsed.get('note', reply_body[:200])
                new_date = parsed.get('suggested_deadline')

                status_map = {
                    'done':     Commitment.Status.DELIVERED,
                    'deferred': Commitment.Status.DEFERRED,
                    'blocked':  Commitment.Status.AT_RISK,
                    'active':   Commitment.Status.ACTIVE,
                }
                new_status = status_map.get(intent)

                update_fields = ['updated_at']
                if new_status and new_status != commitment.status:
                    commitment.status = new_status
                    update_fields.append('status')
                if new_date:
                    from datetime import date as date_type
                    import datetime
                    try:
                        commitment.deadline = datetime.date.fromisoformat(new_date)
                        update_fields.append('deadline')
                    except ValueError:
                        pass
                if len(update_fields) > 1:
                    commitment.save(update_fields=update_fields)

                CommitmentEvent.objects.create(
                    commitment=commitment,
                    event_type=CommitmentEvent.EventType.FIELD_EDITED,
                    note=f'[Gmail reply — auto-parsed] {note}',
                    new_value={'intent': intent, 'suggested_deadline': new_date},
                )

                owner      = commitment.owner
                owner_name = owner.name if owner else 'Owner'
                intent_label = {
                    'done':     'marked it Done',
                    'deferred': 'requested a deadline extension',
                    'blocked':  'reported a blocker',
                }.get(intent, f'replied ({intent})')
                from apps.notifications.views import create_cos_notification
                create_cos_notification(
                    org, commitment,
                    f'{owner_name} {intent_label} on "{commitment.normalised_text[:80]}" via email.',
                    'gmail_reply',
                )

                # Mark this message as processed so it is not re-handled on the next poll
                if reply.get('message_id'):
                    nl.last_reply_message_id = reply['message_id']
                    nl.save(update_fields=['last_reply_message_id'])

                poll_log.replies_found      += 1
                poll_log.commitments_updated += 1
                total_updated               += 1

        except Exception as exc:
            logger.error("poll_gmail_replies failed for org %s: %s", org.slug, exc)
            poll_log.error = str(exc)

        poll_log.save()

    logger.info("poll_gmail_replies: %d commitments updated across all orgs", total_updated)
    return {'commitments_updated': total_updated}


# ── Google Calendar / Meet ─────────────────────────────────────────────────────

def _build_calendar_credentials(conn):
    """Build Google OAuth2 Credentials from a CalendarConnection, refreshing if expired."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    expiry = None
    if conn.token_expiry:
        # google-auth expects a naive UTC datetime
        expiry = conn.token_expiry.replace(tzinfo=None) if conn.token_expiry.tzinfo else conn.token_expiry

    creds = Credentials(
        token=conn.access_token,
        refresh_token=conn.refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        expiry=expiry,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        conn.access_token = creds.token
        conn.token_expiry = creds.expiry
        conn.save(update_fields=['access_token', 'token_expiry'])
    return creds


@shared_task
def sync_calendar_events():
    """Every 15 min — pull Google Calendar events with Meet links for all connected orgs."""
    from datetime import timedelta
    from django.utils import timezone
    from dateutil.parser import parse as parse_dt
    from googleapiclient.discovery import build
    from .models import CalendarConnection, CalendarEvent

    total_new = total_updated = 0

    for conn in CalendarConnection.objects.select_related('organisation').all():
        org = conn.organisation
        try:
            creds   = _build_calendar_credentials(conn)
            service = build('calendar', 'v3', credentials=creds, cache_discovery=False)

            now      = timezone.now()
            time_min = (now - timedelta(hours=24)).isoformat()
            time_max = (now + timedelta(days=7)).isoformat()

            result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
                maxResults=100,
            ).execute()

            for event in result.get('items', []):
                # Extract Meet link from conferenceData
                meet_link = meet_code = ''
                for ep in event.get('conferenceData', {}).get('entryPoints', []):
                    if ep.get('entryPointType') == 'video':
                        meet_link = ep.get('uri', '')
                        meet_code = meet_link.rstrip('/').split('/')[-1] if meet_link else ''
                        break
                if not meet_link:
                    continue

                starts_at = parse_dt(event['start'].get('dateTime') or event['start']['date'] + 'T00:00:00+00:00')
                ends_at   = parse_dt(event['end'].get('dateTime')   or event['end']['date']   + 'T23:59:59+00:00')
                if starts_at.tzinfo is None:
                    starts_at = timezone.make_aware(starts_at)
                if ends_at.tzinfo is None:
                    ends_at = timezone.make_aware(ends_at)

                cal_event, created = CalendarEvent.objects.get_or_create(
                    organisation=org,
                    google_event_id=event['id'],
                    defaults={
                        'title':     event.get('summary', '(no title)'),
                        'starts_at': starts_at,
                        'ends_at':   ends_at,
                        'meet_link': meet_link,
                        'meet_code': meet_code,
                        'status':    CalendarEvent.Status.PENDING,
                    },
                )

                if created:
                    total_new += 1
                    # Schedule transcript fetch 10 min after event ends (minimum 0 s for past events)
                    delay_s = max(0, int((ends_at - now).total_seconds()) + 600)
                    fetch_google_meet_transcript.apply_async(
                        args=[str(cal_event.id)],
                        countdown=delay_s,
                    )
                    logger.info(
                        "sync_calendar_events: '%s' scheduled for transcript fetch in %ds",
                        cal_event.title, delay_s,
                    )
                else:
                    # Update if the event was rescheduled
                    update_fields = []
                    new_title = event.get('summary', '(no title)')
                    if cal_event.title != new_title:
                        cal_event.title = new_title
                        update_fields.append('title')
                    if cal_event.starts_at != starts_at:
                        cal_event.starts_at = starts_at
                        update_fields.append('starts_at')
                    if cal_event.ends_at != ends_at:
                        cal_event.ends_at = ends_at
                        update_fields.append('ends_at')
                    if update_fields:
                        update_fields.append('updated_at')
                        cal_event.save(update_fields=update_fields)
                        total_updated += 1

            conn.last_synced_at = now
            conn.save(update_fields=['last_synced_at'])

        except Exception as exc:
            logger.error("sync_calendar_events failed for org %s: %s", org.slug, exc)

    logger.info("sync_calendar_events: %d new, %d updated", total_new, total_updated)
    return {'new': total_new, 'updated': total_updated}


@shared_task(bind=True, max_retries=2)
def fetch_google_meet_transcript(self, calendar_event_id: str):
    """
    Search Drive for a Meet transcript for a CalendarEvent, then create a Meeting
    and queue process_meeting. Retries twice (5 min apart) on transient failures.
    """
    from datetime import timedelta
    from googleapiclient.discovery import build
    from .models import CalendarConnection, CalendarEvent
    from apps.meetings.models import Meeting

    try:
        cal_event = CalendarEvent.objects.select_related('organisation').get(id=calendar_event_id)
    except CalendarEvent.DoesNotExist:
        logger.error("fetch_google_meet_transcript: event %s not found", calendar_event_id)
        return

    if cal_event.status in {CalendarEvent.Status.DONE, CalendarEvent.Status.PROCESSING}:
        return

    org = cal_event.organisation

    try:
        conn = CalendarConnection.objects.get(organisation=org)
    except CalendarConnection.DoesNotExist:
        logger.warning("fetch_google_meet_transcript: no CalendarConnection for org %s", org.slug)
        cal_event.status = CalendarEvent.Status.FAILED
        cal_event.error  = 'Calendar not connected'
        cal_event.save(update_fields=['status', 'error', 'updated_at'])
        return

    cal_event.status = CalendarEvent.Status.FETCHING
    cal_event.save(update_fields=['status', 'updated_at'])

    try:
        creds = _build_calendar_credentials(conn)
        drive = build('drive', 'v3', credentials=creds, cache_discovery=False)

        # Search Drive for transcript docs created on or after meeting start
        cutoff = (cal_event.starts_at - timedelta(minutes=5)).isoformat()
        results = drive.files().list(
            q=(
                f"name contains 'Transcript' and "
                f"mimeType='application/vnd.google-apps.document' and "
                f"createdTime > '{cutoff}'"
            ),
            fields='files(id,name,createdTime)',
            orderBy='createdTime desc',
            pageSize=20,
        ).execute()
        files = results.get('files', [])

        # Match by meet code or title keywords; fall back to most recent
        transcript_file_id = transcript_title = ''
        title_words = [w for w in cal_event.title.lower().split() if len(w) > 3]
        for f in files:
            name_lower = f['name'].lower()
            if (cal_event.meet_code and cal_event.meet_code.lower() in name_lower) or \
               any(w in name_lower for w in title_words):
                transcript_file_id = f['id']
                transcript_title   = f['name']
                break
        if not transcript_file_id and files:
            transcript_file_id = files[0]['id']
            transcript_title   = files[0]['name']

        if not transcript_file_id:
            cal_event.status = CalendarEvent.Status.NO_TRANSCRIPT
            cal_event.save(update_fields=['status', 'updated_at'])
            logger.info("fetch_google_meet_transcript: no transcript for '%s'", cal_event.title)
            return

        cal_event.drive_file_id = transcript_file_id
        cal_event.status        = CalendarEvent.Status.PROCESSING
        cal_event.save(update_fields=['drive_file_id', 'status', 'updated_at'])

        content = drive.files().export(
            fileId=transcript_file_id,
            mimeType='text/plain',
        ).execute()
        transcript_text = content.decode('utf-8', errors='replace') if isinstance(content, bytes) else str(content)

        if not transcript_text.strip():
            cal_event.status = CalendarEvent.Status.NO_TRANSCRIPT
            cal_event.error  = 'Transcript file was empty'
            cal_event.save(update_fields=['status', 'error', 'updated_at'])
            return

        meeting = Meeting.objects.create(
            organisation=org,
            title=cal_event.title or transcript_title,
            platform=Meeting.Platform.UPLOAD,
            occurred_at=cal_event.starts_at,
            raw_transcript=transcript_text,
            word_count=len(transcript_text.split()),
            external_id=cal_event.google_event_id,
            external_url=cal_event.meet_link,
        )

        cal_event.meeting = meeting
        cal_event.status  = CalendarEvent.Status.DONE
        cal_event.save(update_fields=['meeting', 'status', 'updated_at'])

        from apps.meetings.tasks import process_meeting
        process_meeting.delay(str(meeting.id))

        logger.info(
            "fetch_google_meet_transcript: created meeting %s from '%s' for org %s",
            meeting.id, cal_event.title, org.slug,
        )

    except Exception as exc:
        logger.error("fetch_google_meet_transcript failed for event %s: %s", calendar_event_id, exc)
        try:
            cal_event.status = CalendarEvent.Status.FAILED
            cal_event.error  = str(exc)[:500]
            cal_event.save(update_fields=['status', 'error', 'updated_at'])
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=300)
