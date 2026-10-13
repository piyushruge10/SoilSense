from django.contrib import admin

from .models import PlantCare, SensorData, SerialConfiguration, SharedSoilSettings

admin.site.site_header = "SoilSense Control Room"
admin.site.site_title = "SoilSense Admin"
admin.site.index_title = "Platform management"


@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ("user", "temperature", "humidity", "moisture", "recorded_at")
    list_filter = ("recorded_at",)
    search_fields = ("user__username", "user__email")
    date_hierarchy = "recorded_at"


@admin.register(PlantCare)
class PlantCareAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "temperature_min", "temperature_max")
    list_filter = ("category",)
    search_fields = ("name", "category", "care_tips")


@admin.register(SerialConfiguration)
class SerialConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "port",
        "baud_rate",
        "moisture_threshold",
        "sample_interval",
    )
    search_fields = ("user__username", "port")
    list_select_related = ("user",)


@admin.register(SharedSoilSettings)
class SharedSoilSettingsAdmin(admin.ModelAdmin):
    list_display = ("user", "is_published", "token")
    list_filter = ("is_published",)
    search_fields = ("user__username", "user__email", "token")
    list_editable = ("is_published",)
    list_select_related = ("user",)
    readonly_fields = ("token",)
