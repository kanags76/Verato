import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_emailotp_purpose_email_verification'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MeetingManager',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4, editable=False, primary_key=True, serialize=False,
                )),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined')],
                    default='pending',
                    max_length=10,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('organisation', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='meeting_managers',
                    to='accounts.organisation',
                )),
                ('manager_user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='manages_for',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('managed_user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='delegated_to',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'db_table': 'accounts_meetingmanager'},
        ),
        migrations.AlterUniqueTogether(
            name='meetingmanager',
            unique_together={('organisation', 'manager_user', 'managed_user')},
        ),
    ]
