from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_nudgelog_type_person'),
    ]

    operations = [
        migrations.CreateModel(
            name='NudgeDashboard',
            fields=[],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
                'verbose_name': 'Nudge Dashboard',
                'verbose_name_plural': 'Nudge Dashboard',
            },
            bases=('notifications.nudgelog',),
        ),
    ]
