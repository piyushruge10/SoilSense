import django.core.validators
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0008_serialconfiguration_ingest_key")]

    operations = [
        migrations.AlterField(
            "sensordata", "temperature", models.FloatField(blank=True, null=True)
        ),
        migrations.AlterField(
            "sensordata", "humidity", models.FloatField(blank=True, null=True)
        ),
        migrations.AlterField(
            "sensordata",
            "moisture",
            models.FloatField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(100),
                ],
            ),
        ),
        migrations.AlterField(
            "sensordata",
            "recorded_at",
            models.DateTimeField(
                db_index=True, default=django.utils.timezone.now, editable=False
            ),
        ),
    ]
