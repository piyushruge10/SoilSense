from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("control/", views.admin_dashboard, name="admin-dashboard"),
    path("plants/", views.plants, name="plants"),
    path("signup/", views.signup, name="signup"),
    path("share/", views.live_share, name="live-share"),
    path("share/settings/", views.update_live_share, name="update-live-share"),
    path("share/<uuid:token>/", views.shared_soil_page, name="shared-soil"),
    path("settings/", views.settings_page, name="settings"),
    path("api/sensor-data/", views.sensor_data_api, name="sensor-data"),
    path("api/public-sensor-data/<uuid:token>/", views.public_sensor_data_api, name="public-sensor-data"),
]
