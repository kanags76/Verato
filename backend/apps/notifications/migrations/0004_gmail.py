import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0003_nudgedashboard_proxy'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='nudgelog',
            name='gmail_thread_id',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.CreateModel(
            name='GmailPollLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('polled_at', models.DateTimeField(auto_now_add=True)),
                ('threads_checked', models.IntegerField(default=0)),
                ('replies_found', models.IntegerField(default=0)),
                ('commitments_updated', models.IntegerField(default=0)),
                ('error', models.TextField(blank=True)),
                ('organisation', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='gmail_poll_logs',
                    to='accounts.organisation',
                )),
            ],
            options={'db_table': 'notifications_gmailpolllog', 'ordering': ['-polled_at']},
        ),
    ]
