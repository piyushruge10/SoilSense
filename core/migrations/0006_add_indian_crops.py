from django.db import migrations


CROPS_BY_CATEGORY = {
    "Indian cereal": [
        "Wheat",
        "Rice",
        "Maize",
        "Barley",
        "Oats",
        "Sorghum (Jowar)",
        "Pearl Millet (Bajra)",
        "Finger Millet (Ragi)",
        "Foxtail Millet",
        "Barnyard Millet",
        "Kodo Millet",
        "Little Millet",
        "Proso Millet",
        "Buckwheat",
    ],
    "Indian pulse": [
        "Chickpea (Chana)",
        "Pigeon Pea (Arhar)",
        "Green Gram (Moong)",
        "Black Gram (Urad)",
        "Lentil (Masoor)",
        "Cowpea (Lobia)",
        "Moth Bean",
        "Horse Gram",
        "Field Pea",
        "Kidney Bean (Rajma)",
        "Lathyrus (Khesari)",
        "Hyacinth Bean (Sem)",
        "Rice Bean",
        "Cluster Bean (Guar)",
        "Winged Bean",
    ],
    "Indian oilseed": [
        "Mustard",
        "Groundnut",
        "Sesame",
        "Castor",
        "Linseed (Flax)",
        "Safflower",
        "Niger Seed",
        "Rapeseed",
        "Soybean",
        "Oil Palm",
    ],
    "Indian cash crop": [
        "Cotton",
        "Sugarcane",
        "Jute",
        "Tobacco",
        "Tea",
        "Coffee",
        "Natural Rubber",
        "Indigo",
    ],
    "Indian spice": [
        "Turmeric",
        "Ginger",
        "Cumin",
        "Coriander",
        "Fenugreek",
        "Black Pepper",
        "Green Cardamom",
        "Clove",
        "Cinnamon",
        "Red Chili",
        "Ajwain",
        "Curry Leaf",
    ],
    "Indian vegetable": [
        "Okra",
        "Bitter Gourd",
        "Bottle Gourd",
        "Ridge Gourd",
        "Sponge Gourd",
        "Snake Gourd",
        "Ash Gourd",
        "Indian Eggplant",
        "Drumstick (Moringa)",
        "Taro",
        "Elephant Foot Yam",
        "Greater Yam",
        "Amaranth Greens",
        "Pointed Gourd",
        "Ivy Gourd",
        "Malabar Spinach",
    ],
    "Indian fruit": [
        "Guava",
        "Papaya",
        "Banana",
        "Pomegranate",
        "Jackfruit",
        "Indian Gooseberry (Amla)",
        "Sapodilla (Chikoo)",
        "Litchi",
        "Jamun",
        "Custard Apple",
        "Kokum",
        "Indian Jujube (Ber)",
        "Bael",
        "Pineapple",
        "Indian Date Palm",
    ],
    "Indian fodder crop": [
        "Berseem Clover",
        "Lucerne (Alfalfa)",
        "Napier Grass",
        "Guinea Grass",
        "Stylo (Stylosanthes)",
        "Fodder Sorghum",
        "Fodder Maize",
        "Fodder Oats",
        "Fodder Pearl Millet",
        "Fodder Cowpea",
    ],
}

CARE_RANGES = {
    "Indian cereal": {
        "temperature": (15, 30),
        "humidity": (40, 75),
        "moisture": (35, 70),
        "care_tips": "These are broad growing-season ranges; variety, season, and region matter. Rice often needs managed standing water or saturated soil, which a volumetric moisture percentage alone does not describe. Follow local agricultural guidance for irrigation and drainage.",
    },
    "Indian pulse": {
        "temperature": (18, 32),
        "humidity": (35, 70),
        "moisture": (25, 55),
        "care_tips": "Most pulses grow best in well-drained soil and are sensitive to prolonged waterlogging. Water to support establishment, flowering, and pod development; local variety and monsoon timing change requirements.",
    },
    "Indian oilseed": {
        "temperature": (18, 32),
        "humidity": (35, 70),
        "moisture": (25, 60),
        "care_tips": "Use a locally adapted variety and well-drained soil. Keep moisture available during establishment and flowering, while avoiding waterlogging; irrigation needs vary widely among oilseed crops.",
    },
    "Indian cash crop": {
        "temperature": (18, 32),
        "humidity": (45, 80),
        "moisture": (35, 75),
        "care_tips": "This group includes crops with very different climates and growing periods. Treat the displayed ranges as general context only and follow regional agricultural recommendations for the selected crop.",
    },
    "Indian spice": {
        "temperature": (18, 32),
        "humidity": (45, 80),
        "moisture": (35, 70),
        "care_tips": "Many tropical spices prefer warm conditions and moisture-retentive but well-drained soil; cumin and fenugreek generally favor drier conditions. Adjust watering to the specific crop, soil, and season.",
    },
    "Indian vegetable": {
        "temperature": (18, 32),
        "humidity": (40, 75),
        "moisture": (35, 70),
        "care_tips": "Grow in fertile, well-draining soil and keep moisture reasonably steady during active growth. Gourd, leafy, and tuber crops have different schedules, so adapt watering to crop stage and local weather.",
    },
    "Indian fruit": {
        "temperature": (18, 32),
        "humidity": (40, 80),
        "moisture": (30, 70),
        "care_tips": "Fruit trees and tropical fruit crops differ substantially in climate, soil, and irrigation needs. Use the broad range as a reference, and follow local guidance for the crop and its growth stage.",
    },
    "Indian fodder crop": {
        "temperature": (18, 32),
        "humidity": (35, 75),
        "moisture": (35, 70),
        "care_tips": "Choose a fodder species suited to the season and livestock system. Maintain moisture for establishment and regrowth without waterlogging; cutting frequency and local climate affect crop needs.",
    },
}


def add_crops(apps, schema_editor):
    PlantCare = apps.get_model("core", "PlantCare")
    database = schema_editor.connection.alias
    crops = []
    for category, names in CROPS_BY_CATEGORY.items():
        guidance = CARE_RANGES[category]
        for name in names:
            crops.append(
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
    PlantCare.objects.using(database).bulk_create(crops, ignore_conflicts=True)


def remove_crops(apps, schema_editor):
    PlantCare = apps.get_model("core", "PlantCare")
    names = [name for group in CROPS_BY_CATEGORY.values() for name in group]
    PlantCare.objects.using(schema_editor.connection.alias).filter(
        name__in=names
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0005_add_common_plants")]

    operations = [migrations.RunPython(add_crops, remove_crops)]
