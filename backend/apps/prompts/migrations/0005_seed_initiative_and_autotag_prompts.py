from django.db import migrations

AUTO_TAG = (
    'You are a tagging assistant for an executive commitment tracker.\n\n'
    'Commitment: "{commitment_text}"\n\n'
    'Existing tags in this organisation: {existing_tags}\n\n'
    'Return a JSON array of 1-4 lowercase tag labels that best categorise this commitment. '
    'Reuse existing tags where appropriate. Only create a new tag if the commitment clearly '
    'belongs to a theme not covered by existing tags. Keep labels short (1-3 words). '
    'Return ONLY the JSON array, nothing else. Example: ["product", "q2 roadmap"]'
)

INITIATIVE_SUMMARY = (
    'You are summarising the status of a strategic initiative called "{initiative_label}" '
    'for a Chief of Staff.\n\n'
    'Initiative description: {description}\n\n'
    'Active commitments under this initiative:\n{commitments_list}\n\n'
    'Write a 2-3 sentence summary covering: overall health (on track / at risk / blocked), '
    'key upcoming deadlines, and any red flags. Be direct and factual. No fluff.'
)


def seed(apps, schema_editor):
    Prompt = apps.get_model('prompts', 'Prompt')
    Prompt.objects.get_or_create(name='auto_tag',            defaults={'content': AUTO_TAG})
    Prompt.objects.get_or_create(name='initiative_summary',  defaults={'content': INITIATIVE_SUMMARY})


class Migration(migrations.Migration):

    dependencies = [
        ('prompts', '0004_add_meeting_title_to_prompts'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
