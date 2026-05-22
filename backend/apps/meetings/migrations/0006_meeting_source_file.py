from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meetings', '0005_pending_clarification_and_clarification_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='meeting',
            name='source_file',
            field=models.FileField(blank=True, null=True, upload_to='meeting_files/'),
        ),
    ]
