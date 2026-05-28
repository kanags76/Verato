from django.db import migrations

WEEKLY_DIGEST_INTRO = (
    "Write a 2-3 sentence executive summary for {org_name}'s weekly commitment digest. "
    "{overdue_count} overdue, {at_risk_count} at-risk, {on_track_count} on-track. "
    "Be concise and action-oriented. Plain text only."
)


def seed(apps, schema_editor):
    Prompt = apps.get_model('prompts', 'Prompt')
    Prompt.objects.get_or_create(
        name='weekly_digest_intro',
        defaults={'content': WEEKLY_DIGEST_INTRO},
    )


class Migration(migrations.Migration):

    dependencies = [
        ('prompts', '0006_aicalllog'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
