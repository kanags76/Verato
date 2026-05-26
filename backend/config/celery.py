import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

app = Celery('commitment_os')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'recompute-risk-scores': {
        'task':     'apps.commitments.tasks.recompute_risk_scores',
        'schedule': crontab(minute=0, hour='*/24'),
    },
    'send-deadline-nudges': {
        'task':     'apps.notifications.tasks.send_deadline_nudges',
        'schedule': crontab(minute=0, hour=9),
    },
    'send-weekly-digest': {
        'task':     'apps.notifications.tasks.send_weekly_digest',
        'schedule': crontab(minute=0, hour=7, day_of_week='monday'),
    },
    'poll-gmail-replies': {
        'task':     'apps.notifications.tasks.poll_gmail_replies',
        'schedule': crontab(minute='*/15'),  # every 15 min — per-org interval enforced in task
    },
    'sync-calendar-events': {
        'task':     'apps.notifications.tasks.sync_calendar_events',
        'schedule': crontab(minute='*/15'),  # every 15 min — picks up new Meet events
    },
    'poll-slack-replies': {
        'task':     'apps.notifications.tasks.poll_slack_replies',
        'schedule': crontab(minute='*/15'),  # every 15 min — checks Slack DM threads for owner replies
    },
}
