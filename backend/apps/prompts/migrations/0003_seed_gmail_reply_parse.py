from django.db import migrations

GMAIL_REPLY_PARSE = '''An owner replied to a commitment reminder email. Extract a structured update.

COMMITMENT: {commitment_text}
DEADLINE: {deadline_str}

REPLY EMAIL:
{reply_body}

Return JSON only (no markdown):
{
  "intent": "done" | "active" | "deferred" | "blocked" | "no_update",
  "note": "1-2 sentence summary of what the owner said",
  "suggested_deadline": "YYYY-MM-DD if they mentioned a new date, else null"
}

intent meanings:
  done      — owner says it is complete or delivered
  active    — owner confirms they are on track
  deferred  — owner is pushing the deadline out
  blocked   — owner is stuck and needs help
  no_update — reply does not contain a meaningful status update'''


def seed(apps, schema_editor):
    Prompt = apps.get_model('prompts', 'Prompt')
    Prompt.objects.get_or_create(name='gmail_reply_parse', defaults={'content': GMAIL_REPLY_PARSE})


class Migration(migrations.Migration):

    dependencies = [
        ('prompts', '0002_seed_prompts'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
