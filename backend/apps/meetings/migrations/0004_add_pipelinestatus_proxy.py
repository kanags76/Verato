from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('meetings', '0003_meeting_pending_participants_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='PipelineStatus',
            fields=[],
            options={
                'verbose_name': 'Pipeline Status',
                'verbose_name_plural': '⚙ Pipeline Status',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('meetings.meeting',),
        ),
    ]
