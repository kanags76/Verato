from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0007_add_calendar_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inappnotification',
            name='notification_type',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('slack_reply',    'Slack Reply'),
                    ('gmail_reply',    'Gmail Reply'),
                    ('meeting_ready',  'Meeting Ready'),
                    ('meeting_failed', 'Meeting Failed'),
                ],
            ),
        ),
    ]
