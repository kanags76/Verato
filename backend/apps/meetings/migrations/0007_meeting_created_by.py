import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_created_by(apps, schema_editor):
    """Set created_by to the org's first admin for all meetings that have no owner."""
    Meeting = apps.get_model('meetings', 'Meeting')
    User = apps.get_model('accounts', 'User')

    org_admin_map = {}
    for meeting in Meeting.objects.filter(created_by__isnull=True):
        org_id = meeting.organisation_id
        if org_id not in org_admin_map:
            admin = User.objects.filter(
                organisation_id=org_id, is_org_admin=True,
            ).order_by('date_joined').first()
            org_admin_map[org_id] = admin
        admin = org_admin_map.get(org_id)
        if admin:
            meeting.created_by = admin
            meeting.save(update_fields=['created_by'])


class Migration(migrations.Migration):

    dependencies = [
        ('meetings', '0006_meeting_source_file'),
        ('accounts', '0007_meetingmanager'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='meeting',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='owned_meetings',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(backfill_created_by, migrations.RunPython.noop),
    ]
