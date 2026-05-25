import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_person_email_nullable'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='terms_accepted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='EmailOTP',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=6)),
                ('purpose', models.CharField(
                    choices=[('login', 'Login'), ('password_reset', 'Password Reset')],
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('attempts', models.IntegerField(default=0)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='otps',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'db_table': 'accounts_emailotp'},
        ),
        migrations.AddIndex(
            model_name='emailotp',
            index=models.Index(
                fields=['user', 'purpose', 'created_at'],
                name='emailotp_user_purpose_idx',
            ),
        ),
    ]
