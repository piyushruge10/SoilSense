import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import PlantCare, SensorData, SerialConfiguration, SharedSoilSettings
from .readings import parse_reading


class ReadingParsingTests(TestCase):
    def test_parses_csv_and_json_readings(self):
        self.assertEqual(parse_reading("21.5,60,37"), (21.5, 60.0, 37.0))
        self.assertEqual(
            parse_reading('{"temperature":21.5,"humidity":60,"moisture":37}'),
            (21.5, 60.0, 37.0),
        )

    def test_unresponsive_sensor_is_reported_as_missing(self):
        self.assertEqual(parse_reading("nan,60,37"), (None, 60.0, 37.0))
        self.assertEqual(parse_reading("21.5,101,37"), (21.5, None, 37.0))
        self.assertEqual(parse_reading("21.5,60,"), (21.5, 60.0, None))
        self.assertEqual(parse_reading("-127,60,37"), (None, 60.0, 37.0))

    def test_rejects_malformed_or_fully_empty_readings(self):
        self.assertIsNone(parse_reading("not sensor data"))
        self.assertIsNone(parse_reading("nan,nan,nan"))


class DashboardTests(TestCase):
    def test_authenticated_pages_include_app_launcher_and_author_credit(self):
        self._sign_in()

        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, "my-friends-katta.onrender.com")
        self.assertContains(response, "My Friends Katta")
        self.assertContains(response, 'target="_blank"')
        self.assertContains(response, "Made by Piyush Ruge")
        self.assertContains(response, 'class="app-grid-icon"')
        icon = re.search(
            rb'<span class="app-grid-icon" aria-hidden="true">(.*?)</span>',
            response.content,
            re.DOTALL,
        )
        self.assertIsNotNone(icon)
        self.assertEqual(icon.group(1).count(b"<i></i>"), 9)
        self.assertContains(response, "theme-toggle")

    def test_admin_dashboard_summarizes_app_settings_for_staff(self):
        staff_user = get_user_model().objects.create_user(
            username="staff-grower", password="test-password", is_staff=True
        )
        self.client.force_login(staff_user)
        SerialConfiguration.objects.create(user=staff_user, port="COM4")
        SharedSoilSettings.objects.create(user=staff_user, is_published=True)
        PlantCare.objects.create(
            name="Admin Test Plant",
            category="Test",
            temperature_min=10,
            temperature_max=30,
            humidity_min=20,
            humidity_max=80,
            moisture_min=20,
            moisture_max=80,
            care_tips="Test guide.",
        )

        response = self.client.get(reverse("admin-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SoilSense administration")
        self.assertContains(response, "Manage users")
        self.assertContains(response, "Device settings")
        self.assertContains(response, "Plant care library")
        self.assertContains(response, "Sharing controls")
        self.assertContains(response, reverse("admin:core_serialconfiguration_changelist"))

    def test_admin_dashboard_is_forbidden_to_non_staff_users(self):
        self._sign_in()

        response = self.client.get(reverse("admin-dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response.url)

    def test_django_admin_index_uses_custom_branding_and_styles(self):
        administrator = get_user_model().objects.create_superuser(
            username="admin-grower",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(administrator)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SoilSense")
        self.assertContains(response, "Platform management")
        self.assertContains(response, "SOILSENSE / CONTROL ROOM")
        self.assertContains(response, "/static/core/admin.css")
        self.assertContains(response, "Open control center")
        self.assertContains(response, "Shared soil settings")

    def test_dashboard_shows_only_the_signed_in_users_readings(self):
        owner = get_user_model().objects.create_user(
            username="another-grower", password="test-password"
        )
        user = self._sign_in()
        SensorData.objects.create(
            user=owner, temperature=30, humidity=40, moisture=25
        )
        SensorData.objects.create(
            user=user, temperature=21.5, humidity=60, moisture=37
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "21.5")
        self.assertContains(response, "37.0%")
        self.assertNotContains(response, "30.0")

    def test_dashboard_marks_a_missing_sensor(self):
        user = self._sign_in()
        SensorData.objects.create(user=user, temperature=None, humidity=60, moisture=37)

        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, "No sensor readings found")
        self.assertContains(response, "60.0")
        self.assertContains(response, "37.0")

    def test_plant_search_filters_guides(self):
        self._sign_in()
        PlantCare.objects.create(
            name="Test Basil",
            category="Herb",
            temperature_min=18,
            temperature_max=28,
            humidity_min=40,
            humidity_max=70,
            moisture_min=35,
            moisture_max=60,
            care_tips="Keep the soil evenly moist.",
        )
        PlantCare.objects.create(
            name="Test Fern",
            category="Houseplant",
            temperature_min=16,
            temperature_max=24,
            humidity_min=60,
            humidity_max=90,
            moisture_min=40,
            moisture_max=70,
            care_tips="Keep humidity high.",
        )

        response = self.client.get(reverse("plants"), {"q": "test basil"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Basil")
        self.assertNotContains(response, "Test Fern")

    def test_common_plant_library_includes_one_hundred_additional_plants(self):
        self._sign_in()

        response = self.client.get(reverse("plants"))

        self.assertEqual(PlantCare.objects.count(), 204)
        self.assertContains(response, "Cilantro")
        self.assertContains(response, "Olive Tree")

    def test_plant_library_includes_one_hundred_indian_crops(self):
        self._sign_in()

        response = self.client.get(reverse("plants"))

        self.assertEqual(PlantCare.objects.count(), 204)
        self.assertContains(response, "Wheat")
        self.assertContains(response, "Rice")
        self.assertContains(response, "Sorghum (Jowar)")
        self.assertContains(response, "Indian fodder crop")
        rice = PlantCare.objects.get(name="Rice")
        self.assertIn("standing water", rice.care_tips)

    def test_sensor_api_returns_only_the_signed_in_users_readings(self):
        other = get_user_model().objects.create_user(
            username="another-grower", password="test-password"
        )
        user = self._sign_in()
        SensorData.objects.create(
            user=other, temperature=30, humidity=40, moisture=25
        )
        SensorData.objects.create(
            user=user, temperature=21.5, humidity=60, moisture=37
        )

        response = self.client.get(reverse("sensor-data"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["latest"]["moisture"], 37)
        self.assertEqual(len(response.json()["readings"]), 1)

    def test_browser_ingest_accepts_offline_batch_with_original_timestamps(self):
        user = self._sign_in()
        response = self.client.post(
            reverse("browser-ingest"),
            data={"readings": [
                {"recorded_at": "2026-10-24T08:00:00Z", "temperature": None, "humidity": 55, "moisture": 40},
                {"recorded_at": "2026-10-24T08:00:05Z", "temperature": 21, "humidity": 55, "moisture": 41},
            ]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(SensorData.objects.filter(user=user).count(), 2)

    def test_sensor_api_exports_only_the_users_csv_readings(self):
        other = get_user_model().objects.create_user(
            username="another-grower", password="test-password"
        )
        user = self._sign_in()
        SensorData.objects.create(
            user=other, temperature=30, humidity=40, moisture=25
        )
        SensorData.objects.create(
            user=user, temperature=21.5, humidity=60, moisture=37
        )

        response = self.client.get(
            reverse("sensor-data"), {"format": "csv", "period": "24h"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn(b"21.5,60.0,37.0", response.content)
        self.assertNotIn(b"30.0,40.0,25.0", response.content)
        self.assertIn("attachment", response["Content-Disposition"])

    def test_sensor_api_rejects_unknown_time_period(self):
        self._sign_in()

        response = self.client.get(reverse("sensor-data"), {"period": "forever"})

        self.assertEqual(response.status_code, 400)

    def test_plant_category_sort_and_current_condition_filters(self):
        user = self._sign_in()
        SensorData.objects.create(
            user=user,
            temperature=21,
            humidity=55,
            moisture=45,
        )

        response = self.client.get(
            reverse("plants"), {"category": "Indian cereal", "sort": "name-desc"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Wheat")
        self.assertNotContains(response, "Tomato")
        self.assertContains(response, "Match my soil")

    def test_plant_match_uses_the_signed_in_users_latest_reading(self):
        user = self._sign_in()
        SensorData.objects.create(
            user=user, temperature=21, humidity=55, moisture=45
        )

        response = self.client.get(
            reverse("plants"), {"category": "Herb", "match": "1"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Basil")
        self.assertContains(response, "Matches your current conditions")

    def test_settings_page_saves_serial_configuration(self):
        self._sign_in()
        response = self.client.post(
            reverse("settings"),
            {
                "baud_rate": 9600,
                "moisture_threshold": 35,
                "sample_interval": 5,
            },
        )

        self.assertRedirects(response, reverse("settings"))
        page = self.client.get(reverse("settings"))
        self.assertContains(page, "Arduino connection")
        self.assertContains(page, "Arduino UNO hardware connections")
        self.assertContains(page, "Log out")

    def test_settings_ajax_saves_configuration_and_returns_serial_values(self):
        user = self._sign_in()

        response = self.client.post(
            reverse("settings"),
            {
                "baud_rate": 19200,
                "moisture_threshold": 42,
                "sample_interval": 10,
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "ok": True,
                "settings": {
                    "baud_rate": 19200,
                    "moisture_threshold": 42,
                    "sample_interval": 10,
                },
            },
        )
        configuration = SerialConfiguration.objects.get(user=user)
        self.assertEqual(configuration.moisture_threshold, 42)
        self.assertEqual(configuration.sample_interval, 10)

    def test_settings_ajax_reports_invalid_values(self):
        self._sign_in()

        response = self.client.post(
            reverse("settings"),
            {
                "baud_rate": 9600,
                "moisture_threshold": 101,
                "sample_interval": 5,
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("moisture_threshold", response.json()["errors"])

    def test_settings_logout_button_ends_session(self):
        self._sign_in()

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))
        self.assertRedirects(
            self.client.get(reverse("settings")),
            f"{reverse('login')}?next={reverse('settings')}",
        )

    def test_sharing_page_and_sensor_routes_require_login(self):
        owner = get_user_model().objects.create_user(
            username="private-grower", password="test-password"
        )
        profile = SharedSoilSettings.objects.create(user=owner)
        SensorData.objects.create(
            user=owner, temperature=21.5, humidity=60, moisture=37
        )

        for url in (
            reverse("live-share"),
            reverse("shared-soil", args=[profile.token]),
            reverse("public-sensor-data", args=[profile.token]),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f"{reverse('login')}?next={url}")

    def test_published_profiles_appear_in_distinct_read_only_cards(self):
        owner = get_user_model().objects.create_user(
            username="owner-grower", password="test-password"
        )
        other = get_user_model().objects.create_user(
            username="other-grower", password="test-password"
        )
        owner_profile = SharedSoilSettings.objects.create(
            user=owner, is_published=True
        )
        other_profile = SharedSoilSettings.objects.create(
            user=other, is_published=True
        )
        SensorData.objects.create(
            user=owner, temperature=22, humidity=55, moisture=40
        )
        SensorData.objects.create(
            user=other, temperature=18, humidity=70, moisture=62
        )
        self.client.force_login(owner)

        response = self.client.get(reverse("live-share"))

        self.assertContains(response, "owner-grower")
        self.assertContains(response, "other-grower")
        self.assertContains(response, reverse("shared-soil", args=[owner_profile.token]))
        self.assertContains(response, reverse("shared-soil", args=[other_profile.token]))
        self.assertEqual(response.content.count(b'name="action"'), 1)

    def test_owner_can_publish_and_unpublish_own_readings(self):
        owner = self._sign_in()
        profile = SharedSoilSettings.objects.create(user=owner)
        SensorData.objects.create(
            user=owner, temperature=22, humidity=55, moisture=40
        )

        publish = self.client.post(
            reverse("update-live-share"), {"action": "publish"}
        )

        self.assertRedirects(publish, reverse("live-share"))
        self.assertTrue(
            SharedSoilSettings.objects.get(pk=profile.pk).is_published
        )
        self.assertEqual(
            self.client.get(
                reverse("public-sensor-data", args=[profile.token])
            ).json()["latest"]["moisture"],
            40,
        )

        self.client.post(reverse("update-live-share"), {"action": "unpublish"})

        self.assertFalse(
            SharedSoilSettings.objects.get(pk=profile.pk).is_published
        )

    def test_share_links_are_unique_and_other_users_cannot_stop_sharing(self):
        owner = get_user_model().objects.create_user(
            username="owner-grower", password="test-password"
        )
        viewer = get_user_model().objects.create_user(
            username="viewer-grower", password="test-password"
        )
        profile = SharedSoilSettings.objects.create(user=owner, is_published=True)
        SensorData.objects.create(
            user=owner, temperature=22, humidity=55, moisture=40
        )
        self.client.force_login(viewer)

        page = self.client.get(reverse("shared-soil", args=[profile.token]))
        response = self.client.post(
            reverse("update-live-share"), {"action": "unpublish"}
        )

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "22.0")
        self.assertNotContains(page, "Stop sharing")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SharedSoilSettings.objects.get(pk=profile.pk).is_published)
        viewer_profile, _ = SharedSoilSettings.objects.get_or_create(user=viewer)
        self.assertNotEqual(profile.token, viewer_profile.token)

    def test_unpublished_share_link_is_not_accessible(self):
        owner = get_user_model().objects.create_user(
            username="private-grower", password="test-password"
        )
        profile = SharedSoilSettings.objects.create(user=owner)
        self._sign_in()

        self.assertEqual(
            self.client.get(reverse("shared-soil", args=[profile.token])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("public-sensor-data", args=[profile.token])
            ).status_code,
            404,
        )

    def test_anonymous_user_cannot_change_publication_state(self):
        self.client.logout()
        response = self.client.post(
            reverse("update-live-share"), {"action": "publish"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
        self.assertFalse(SharedSoilSettings.objects.filter(is_published=True).exists())

    def test_login_and_signup_pages_are_standalone_and_link_to_each_other(self):
        login_page = self.client.get(reverse("login"))
        signup_page = self.client.get(reverse("signup"))

        self.assertContains(login_page, reverse("signup"))
        self.assertContains(signup_page, reverse("login"))
        for response in (login_page, signup_page):
            self.assertNotContains(response, '<aside class="sidebar"')
            self.assertNotContains(response, '<header class="topbar"')
            self.assertNotContains(response, "My Friends Katta")
            self.assertNotContains(response, "Made by Piyush Ruge")

    def test_signup_creates_account_and_share_profile(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "new-grower",
                "password1": "garden-password-482",
                "password2": "garden-password-482",
            },
        )

        self.assertRedirects(response, reverse("login"))
        user = get_user_model().objects.get(username="new-grower")
        self.assertTrue(SharedSoilSettings.objects.filter(user=user).exists())

    def test_all_application_pages_require_login(self):
        self.client.logout()
        for name in (
            "dashboard",
            "plants",
            "settings",
            "live-share",
            "sensor-data",
        ):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response.url)

    def _sign_in(self):
        user = get_user_model().objects.create_user(
            username="test-grower", password="test-password"
        )
        self.client.force_login(user)
        return user
