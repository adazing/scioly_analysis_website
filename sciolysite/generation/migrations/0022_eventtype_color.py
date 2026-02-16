from django.db import migrations, models


PASTEL_COLORS = ["FFE9D0", "FFFED3", "BBE9FF", "B1AFFF", "E7F0DC", "E7D4B5", "EF9C66", "C8CFA0", "E1ACAC", "E1AFD1", "E493B3"]


def assign_colors(apps, schema_editor):
    EventType = apps.get_model('generation', 'EventType')
    for i, et in enumerate(EventType.objects.all().order_by('id')):
        et.color = PASTEL_COLORS[i % len(PASTEL_COLORS)]
        et.save(update_fields=['color'])


class Migration(migrations.Migration):

    dependencies = [
        ('generation', '0021_generatedcompetitionsettings_partner_preference_weight'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventtype',
            name='color',
            field=models.CharField(default='FFE9D0', max_length=6),
        ),
        migrations.RunPython(assign_colors, migrations.RunPython.noop),
    ]
