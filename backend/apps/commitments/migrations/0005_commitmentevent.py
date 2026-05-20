import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_organisation_plan_user_is_org_admin_invitation'),
        ('commitments', '0004_commitment_status_done'),
    ]

    operations = [
        migrations.CreateModel(
            name='CommitmentEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_type', models.CharField(
                    choices=[
                        ('confirmed',    'Confirmed'),
                        ('rejected',     'Rejected'),
                        ('resolved',     'Resolved'),
                        ('reopened',     'Reopened'),
                        ('escalated',    'Escalated'),
                        ('nudged',       'Nudge sent'),
                        ('field_edited', 'Fields edited'),
                    ],
                    max_length=30,
                )),
                ('old_value', models.JSONField(blank=True, null=True)),
                ('new_value', models.JSONField(blank=True, null=True)),
                ('note', models.TextField(blank=True)),
                ('occurred_at', models.DateTimeField(auto_now_add=True)),
                ('commitment', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='events',
                    to='commitments.commitment',
                )),
                ('actor', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='commitment_events',
                    to='accounts.person',
                )),
            ],
            options={
                'db_table': 'commitments_commitmentevent',
                'ordering': ['-occurred_at'],
            },
        ),
    ]
