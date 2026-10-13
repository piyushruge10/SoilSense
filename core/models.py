import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class SensorData(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sensor_readings",
        null=True,
        blank=True,
    )
    temperature = models.FloatField()
    humidity = models.FloatField()
    moisture = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    recorded_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-recorded_at"]
        verbose_name = "sensor reading"
        verbose_name_plural = "sensor readings"

    def __str__(self):
        return f"{self.recorded_at:%Y-%m-%d %H:%M:%S} — {self.moisture:.0f}% moisture"


class PlantCare(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=60, blank=True)
    temperature_min = models.FloatField()
    temperature_max = models.FloatField()
    humidity_min = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    humidity_max = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    moisture_min = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    moisture_max = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    care_tips = models.TextField()

    class Meta:
        ordering = ["name"]
        verbose_name = "plant care guide"

    def __str__(self):
        return self.name


class SerialConfiguration(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="serial_configuration",
        null=True,
        blank=True,
    )
    port = models.CharField(max_length=100, blank=True, help_text="For example COM3")
    baud_rate = models.PositiveIntegerField(default=9600)
    moisture_threshold = models.PositiveSmallIntegerField(
        default=35, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    sample_interval = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(3600)]
    )

    class Meta:
        verbose_name = "serial configuration"

    def __str__(self):
        return self.port or "Serial port not configured"


class SharedSoilSettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shared_soil_settings",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_published = models.BooleanField(default=False)

    class Meta:
        verbose_name = "shared soil settings"
        verbose_name_plural = "shared soil settings"

    def __str__(self):
        return f"Shared soil settings for {self.user}"
