from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0007_alter_sharedsoilsettings_options")]
    operations = [
        migrations.AddField(
            model_name="serialconfiguration",
            name="ingest_key",
            field=models.UUIDField(blank=True, editable=False, null=True, unique=True),
        ),
    ]
