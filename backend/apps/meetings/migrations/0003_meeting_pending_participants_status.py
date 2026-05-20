from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meetings', '0002_meetingtopic_meeting_meeting_type_meeting_summary_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='meeting',
            name='processing_status',
            field=models.CharField(
                choices=[
                    ('pending_participants', 'Awaiting Participant Validation'),
                    ('pending',              'Pending'),
                    ('processing',           'Processing'),
                    ('complete',             'Complete'),
                    ('failed',               'Failed'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]
