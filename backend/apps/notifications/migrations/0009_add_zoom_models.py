import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0008_inappnotification_meeting_types'),
        ('accounts', '0001_initial'),
        ('meetings', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ZoomConnection',
            fields=[
                ('id',              models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('organisation',    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='zoom_connection', to='accounts.organisation')),
                ('access_token',    models.TextField(blank=True)),
                ('refresh_token',   models.TextField(blank=True)),
                ('token_expiry',    models.DateTimeField(blank=True, null=True)),
                ('zoom_email',      models.EmailField(blank=True, max_length=254)),
                ('zoom_account_id', models.CharField(blank=True, max_length=64)),
                ('connected_at',    models.DateTimeField(auto_now_add=True)),
                ('last_event_at',   models.DateTimeField(blank=True, null=True)),
            ],
            options={'db_table': 'notifications_zoomconnection'},
        ),
        migrations.CreateModel(
            name='ZoomRecording',
            fields=[
                ('id',                models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('organisation',      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='zoom_recordings', to='accounts.organisation')),
                ('zoom_meeting_id',   models.CharField(max_length=255)),
                ('zoom_meeting_uuid', models.CharField(blank=True, max_length=255)),
                ('title',             models.CharField(max_length=500)),
                ('started_at',        models.DateTimeField()),
                ('duration_mins',     models.IntegerField(default=0)),
                ('download_url',      models.URLField(blank=True, max_length=2000)),
                ('download_token',    models.TextField(blank=True)),
                ('status',            models.CharField(choices=[('pending', 'Pending'), ('fetching', 'Fetching transcript'), ('processing', 'Processing'), ('done', 'Done'), ('no_transcript', 'No transcript found'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('meeting',           models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='zoom_recording', to='meetings.meeting')),
                ('error',             models.TextField(blank=True)),
                ('created_at',        models.DateTimeField(auto_now_add=True)),
                ('updated_at',        models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'notifications_zoomrecording', 'ordering': ['-started_at']},
        ),
        migrations.AddConstraint(
            model_name='zoomrecording',
            constraint=models.UniqueConstraint(fields=['organisation', 'zoom_meeting_uuid'], name='unique_zoom_recording_per_org'),
        ),
    ]
