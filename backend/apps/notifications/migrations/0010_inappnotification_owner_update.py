from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0009_add_zoom_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inappnotification',
            name='notification_type',
            field=models.CharField(
                choices=[
                    ('slack_reply',    'Slack Reply'),
                    ('gmail_reply',    'Gmail Reply'),
                    ('meeting_ready',  'Meeting Ready'),
                    ('meeting_failed', 'Meeting Failed'),
                    ('owner_update',   'Owner Update'),
                ],
                max_length=20,
            ),
        ),
    ]
