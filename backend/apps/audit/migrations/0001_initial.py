import apps.audit.models
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0004_person_email_nullable'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DataAccessGrant',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('document', models.FileField(
                    help_text='Upload the permission email or signed acknowledgement (PDF, image, or text file)',
                    upload_to='data_access_grants/',
                )),
                ('reason', models.TextField(help_text='Why is this data being accessed?')),
                ('granted_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(
                    default=apps.audit.models._default_expiry,
                    help_text='Access expires at this datetime (default 30 days from now)',
                )),
                ('is_revoked', models.BooleanField(default=False)),
                ('organisation', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='access_grants',
                    to='accounts.organisation',
                )),
                ('granted_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'audit_dataaccessgrant',
                'ordering': ['-granted_at'],
            },
        ),
    ]
