import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='nudgelog',
            name='nudge_type',
            field=models.CharField(
                choices=[
                    ('first_reminder',  'First Reminder'),
                    ('second_reminder', 'Second Reminder'),
                    ('overdue_1',       'Overdue Day +1'),
                    ('overdue_2',       'Overdue Day +2'),
                    ('overdue_3',       'Overdue Day +3'),
                    ('escalation',      'Escalation to CoS'),
                ],
                default='first_reminder',
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='nudgelog',
            name='person',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='nudges_received',
                to='accounts.person',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='nudgelog',
            unique_together={('commitment', 'nudge_type')},
        ),
    ]
