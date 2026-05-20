from django.db import migrations, models


def delivered_to_done(apps, schema_editor):
    Commitment = apps.get_model('commitments', 'Commitment')
    Commitment.objects.filter(status='delivered').update(status='done')


class Migration(migrations.Migration):

    dependencies = [
        ('commitments', '0003_priority_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='commitment',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending_review', 'Pending Review'),
                    ('active', 'Active'),
                    ('at_risk', 'At Risk'),
                    ('escalated', 'Escalated'),
                    ('done', 'Done'),
                    ('deferred', 'Deferred'),
                    ('cancelled', 'Cancelled'),
                ],
                default='pending_review',
                max_length=20,
            ),
        ),
        migrations.RunPython(delivered_to_done, migrations.RunPython.noop),
    ]
