from django.db import migrations


PLANTS = [
    {
        "name": "Basil",
        "category": "Herb",
        "temperature_min": 18,
        "temperature_max": 30,
        "humidity_min": 40,
        "humidity_max": 70,
        "moisture_min": 35,
        "moisture_max": 60,
        "care_tips": "Give basil warmth and bright light. Water when the top layer of soil begins to dry, and avoid waterlogged roots.",
    },
    {
        "name": "Lettuce",
        "category": "Leafy vegetable",
        "temperature_min": 10,
        "temperature_max": 22,
        "humidity_min": 50,
        "humidity_max": 80,
        "moisture_min": 45,
        "moisture_max": 70,
        "care_tips": "Keep the soil consistently moist and provide afternoon shade in warmer weather to reduce bolting.",
    },
    {
        "name": "Mint",
        "category": "Herb",
        "temperature_min": 15,
        "temperature_max": 27,
        "humidity_min": 40,
        "humidity_max": 70,
        "moisture_min": 45,
        "moisture_max": 70,
        "care_tips": "Mint prefers evenly moist soil and partial sun. Grow it in a container to keep its spreading roots in check.",
    },
    {
        "name": "Tomato",
        "category": "Fruit vegetable",
        "temperature_min": 18,
        "temperature_max": 29,
        "humidity_min": 40,
        "humidity_max": 70,
        "moisture_min": 40,
        "moisture_max": 65,
        "care_tips": "Water deeply and consistently at the base of the plant. Mulch to help maintain steady soil moisture.",
    },
]


def add_plants(apps, schema_editor):
    PlantCare = apps.get_model("core", "PlantCare")
    PlantCare.objects.using(schema_editor.connection.alias).bulk_create(
        [PlantCare(**plant) for plant in PLANTS], ignore_conflicts=True
    )


def remove_plants(apps, schema_editor):
    PlantCare = apps.get_model("core", "PlantCare")
    PlantCare.objects.using(schema_editor.connection.alias).filter(
        name__in=[plant["name"] for plant in PLANTS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [migrations.RunPython(add_plants, remove_plants)]
