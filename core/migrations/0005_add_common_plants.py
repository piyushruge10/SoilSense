from django.db import migrations


PLANTS_BY_CATEGORY = {
    "Herb": [
        "Cilantro",
        "Parsley",
        "Rosemary",
        "Thyme",
        "Oregano",
        "Sage",
        "Chives",
        "Dill",
        "Lemongrass",
        "Tarragon",
        "Marjoram",
        "Fennel",
        "Bay Laurel",
        "Chamomile",
        "Lavender",
    ],
    "Vegetable": [
        "Bell Pepper",
        "Cucumber",
        "Carrot",
        "Spinach",
        "Kale",
        "Broccoli",
        "Cauliflower",
        "Cabbage",
        "Radish",
        "Beetroot",
        "Onion",
        "Garlic",
        "Potato",
        "Sweet Potato",
        "Zucchini",
        "Eggplant",
        "Green Bean",
        "Pea",
        "Corn",
        "Celery",
    ],
    "Fruit": [
        "Strawberry",
        "Blueberry",
        "Raspberry",
        "Blackberry",
        "Grape",
        "Watermelon",
        "Cantaloupe",
        "Pumpkin",
        "Apple",
        "Pear",
        "Peach",
        "Plum",
        "Cherry",
        "Lemon",
        "Orange",
    ],
    "Flower": [
        "Marigold",
        "Sunflower",
        "Zinnia",
        "Petunia",
        "Cosmos",
        "Dahlia",
        "Chrysanthemum",
        "Pansy",
        "Snapdragon",
        "Nasturtium",
        "Coneflower",
        "Black-eyed Susan",
        "Geranium",
        "Hibiscus",
        "Rose",
    ],
    "Houseplant": [
        "Monstera",
        "Pothos",
        "Snake Plant",
        "Spider Plant",
        "Peace Lily",
        "ZZ Plant",
        "Rubber Plant",
        "Philodendron",
        "English Ivy",
        "Boston Fern",
        "Fiddle-leaf Fig",
        "Dracaena",
        "Areca Palm",
        "Chinese Evergreen",
        "Alocasia",
        "Calathea",
        "Anthurium",
        "Jade Plant",
        "African Violet",
        "Orchid",
    ],
    "Succulent": [
        "Aloe Vera",
        "Echeveria",
        "Haworthia",
        "Sedum",
        "String of Pearls",
        "Burro's Tail",
        "Panda Plant",
        "Barrel Cactus",
        "Christmas Cactus",
        "Agave",
    ],
    "Tree": [
        "Olive Tree",
        "Japanese Maple",
        "Mango Tree",
        "Avocado Tree",
        "Fig Tree",
    ],
}

CARE_RANGES = {
    "Herb": {
        "temperature": (15, 27),
        "humidity": (40, 65),
        "moisture": (35, 60),
        "care_tips": "Provide bright light and well-draining soil. Water when the top layer begins to dry, adjusting for the plant and local climate.",
    },
    "Vegetable": {
        "temperature": (16, 26),
        "humidity": (45, 75),
        "moisture": (40, 70),
        "care_tips": "Grow in fertile, well-draining soil and keep moisture steady while the plant is actively growing. Sun and seasonal needs vary by crop.",
    },
    "Fruit": {
        "temperature": (15, 28),
        "humidity": (40, 70),
        "moisture": (40, 70),
        "care_tips": "Provide suitable light and well-draining soil. Water deeply during active growth and fruiting, avoiding prolonged waterlogging.",
    },
    "Flower": {
        "temperature": (15, 27),
        "humidity": (40, 70),
        "moisture": (35, 65),
        "care_tips": "Match sunlight to the variety and use well-draining soil. Water at the root zone when the surface begins to dry.",
    },
    "Houseplant": {
        "temperature": (18, 27),
        "humidity": (40, 65),
        "moisture": (30, 60),
        "care_tips": "Keep in suitable indirect light and a draining pot. Check the soil before watering; indoor light and seasonal growth affect needs.",
    },
    "Succulent": {
        "temperature": (18, 30),
        "humidity": (20, 50),
        "moisture": (10, 35),
        "care_tips": "Use a gritty, fast-draining mix and let the soil dry between thorough waterings. Protect from frost unless the species is cold-hardy.",
    },
    "Tree": {
        "temperature": (12, 28),
        "humidity": (35, 70),
        "moisture": (35, 65),
        "care_tips": "Choose a site and soil suited to the species. Water deeply while establishing and account for local climate, season, and mature size.",
    },
}


def add_plants(apps, schema_editor):
    PlantCare = apps.get_model("core", "PlantCare")
    database = schema_editor.connection.alias
    plants = []
    for category, names in PLANTS_BY_CATEGORY.items():
        guidance = CARE_RANGES[category]
        for name in names:
            plants.append(
                PlantCare(
                    name=name,
                    category=category,
                    temperature_min=guidance["temperature"][0],
                    temperature_max=guidance["temperature"][1],
                    humidity_min=guidance["humidity"][0],
                    humidity_max=guidance["humidity"][1],
                    moisture_min=guidance["moisture"][0],
                    moisture_max=guidance["moisture"][1],
                    care_tips=guidance["care_tips"],
                )
            )
    PlantCare.objects.using(database).bulk_create(plants, ignore_conflicts=True)


def remove_plants(apps, schema_editor):
    PlantCare = apps.get_model("core", "PlantCare")
    names = [name for group in PLANTS_BY_CATEGORY.values() for name in group]
    PlantCare.objects.using(schema_editor.connection.alias).filter(
        name__in=names
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0004_remove_serialconfiguration_is_published_and_more")]

    operations = [migrations.RunPython(add_plants, remove_plants)]
