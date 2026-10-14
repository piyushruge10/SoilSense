import csv
from datetime import timedelta
import json
import uuid
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from .serial_monitor import SerialMonitor, available_serial_ports, serial_monitor_for    
from .forms import SerialConfigurationForm
from .models import PlantCare, SensorData, SerialConfiguration, SharedSoilSettings
from .serial_monitor import available_serial_ports, serial_monitor_for


def _configuration(user):
    configuration, created = SerialConfiguration.objects.get_or_create(user=user)
    if created:
        unassigned = SerialConfiguration.objects.filter(user__isnull=True).first()
        if unassigned:
            configuration.delete()
            unassigned.user = user
            unassigned.save(update_fields=["user"])
            configuration = unassigned
        if configuration.ingest_key is None:
            configuration.ingest_key = uuid.uuid4()
            configuration.save(update_fields=["ingest_key"])
    serial_monitor_for(user.pk).configure(
        configuration.port, configuration.baud_rate, user.pk
    )
    return configuration


def dashboard(request):
    readings = list(SensorData.objects.filter(user=request.user)[:24])
    readings.reverse()
    latest = readings[-1] if readings else None
    return render(
        request,
        "core/dashboard.html",
        {
            "latest": latest,
            "readings": readings,
            "serial_status": serial_monitor_for(request.user.pk).status(),
        },
    )


def plants(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    sort = request.GET.get("sort", "name")
    plant_list = PlantCare.objects.all()
    if query:
        plant_list = plant_list.filter(
            Q(name__icontains=query)
            | Q(category__icontains=query)
            | Q(care_tips__icontains=query)
        )
    categories = list(
        PlantCare.objects.order_by("category")
        .values_list("category", flat=True)
        .distinct()
    )
    if category in categories:
        plant_list = plant_list.filter(category=category)
    else:
        category = ""
    if sort == "temperature":
        plant_list = plant_list.order_by("temperature_min", "name")
    elif sort == "moisture":
        plant_list = plant_list.order_by("moisture_min", "name")
    elif sort == "name-desc":
        plant_list = plant_list.order_by("-name")
    else:
        sort = "name"
        plant_list = plant_list.order_by("name")

    latest = SensorData.objects.filter(user=request.user).first()
    match_soil = request.GET.get("match") == "1"
    plant_entries = list(plant_list)
    matching_plant_ids = set()
    if latest:
        matching_plant_ids = {
            plant.pk
            for plant in plant_entries
            if plant.temperature_min <= latest.temperature <= plant.temperature_max
            and plant.humidity_min <= latest.humidity <= plant.humidity_max
            and plant.moisture_min <= latest.moisture <= plant.moisture_max
        }
        if match_soil:
            plant_entries = [
                plant for plant in plant_entries if plant.pk in matching_plant_ids
            ]
    return render(
        request,
        "core/plants.html",
        {
            "plants": plant_entries,
            "query": query,
            "categories": categories,
            "selected_category": category,
            "sort": sort,
            "match_soil": match_soil,
            "has_reading": latest is not None,
            "matching_plant_ids": matching_plant_ids,
            "result_count": len(plant_entries),
        },
    )


@staff_member_required
def admin_dashboard(request):
    return render(
        request,
        "core/admin_dashboard.html",
        {
            "user_count": get_user_model().objects.count(),
            "plant_count": PlantCare.objects.count(),
            "reading_count": SensorData.objects.count(),
            "published_count": SharedSoilSettings.objects.filter(
                is_published=True
            ).count(),
            "serial_configuration_count": SerialConfiguration.objects.count(),
        },
    )


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            SharedSoilSettings.objects.create(user=user)
            messages.success(request, "Your account is ready. Sign in to publish your soil readings.")
            return redirect("login")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


def live_share(request):
    own_profile, _ = SharedSoilSettings.objects.get_or_create(user=request.user)
    published_profiles = list(
        SharedSoilSettings.objects.filter(is_published=True).select_related("user")
    )
    readings = {}
    for reading in SensorData.objects.filter(
        user__in=[profile.user_id for profile in published_profiles]
    ).order_by("user_id", "-recorded_at"):
        readings.setdefault(reading.user_id, reading)
    profiles = [
        {"profile": profile, "latest": readings.get(profile.user_id)}
        for profile in published_profiles
    ]
    latest = readings.get(request.user.pk) if own_profile.is_published else None
    return render(
        request,
        "core/live_share.html",
        {
            "profile": own_profile,
            "profiles": profiles,
            "is_published": own_profile.is_published,
            "latest": latest,
        },
    )


@login_required
@require_POST
def update_live_share(request):
    action = request.POST.get("action")
    if action not in {"publish", "unpublish"}:
        return HttpResponseBadRequest("Choose whether to publish or unpublish readings.")
    profile, _ = SharedSoilSettings.objects.get_or_create(user=request.user)
    profile.is_published = action == "publish"
    profile.save(update_fields=["is_published"])
    if profile.is_published:
        messages.success(request, "Your latest soil readings are now publicly visible.")
    else:
        messages.success(request, "Your soil readings are no longer publicly visible.")
    return redirect("live-share")


@require_GET
def public_sensor_data_api(request, token):
    profile = SharedSoilSettings.objects.filter(token=token, is_published=True).first()
    if profile is None:
        raise Http404
    latest = SensorData.objects.filter(user=profile.user).first()
    return JsonResponse({"latest": _serialize_reading(latest)})


def shared_soil_page(request, token):
    profile = SharedSoilSettings.objects.filter(
        token=token, is_published=True
    ).select_related("user").first()
    if profile is None:
        raise Http404
    return render(
        request,
        "core/shared_soil.html",
        {
            "profile": profile,
            "latest": SensorData.objects.filter(user=profile.user).first(),
        },
    )


def settings_page(request):
    configuration = _configuration(request.user)
    monitor = serial_monitor_for(request.user.pk)
    if request.method == "POST":
        if request.POST.get("action") == "retry":
            if configuration.port:
                monitor.reconnect()
                messages.info(request, f"Retrying connection to {configuration.port}.")
            else:
                messages.error(request, "Select and save a serial port before retrying.")
            return redirect("settings")
        form = SerialConfigurationForm(request.POST, instance=configuration)
        if form.is_valid():
            configuration = form.save()
            monitor.configure(configuration.port, configuration.baud_rate, request.user.pk)
            if configuration.port:
                try:
                    monitor.send_configuration(
                        configuration.moisture_threshold, configuration.sample_interval
                    )
                except RuntimeError as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(request, "Settings saved and queued for the Arduino.")
            else:
                messages.success(request, "Settings saved. Add a serial port to connect the Arduino.")
            return redirect("settings")
    else:
        form = SerialConfigurationForm(instance=configuration)
    return render(
        request,
        "core/settings.html",
        {
            "form": form,
            "serial_status": monitor.status(),
            "available_ports": available_serial_ports(),
            "ingest_key": configuration.ingest_key
        },
    )


@require_GET
def sensor_data_api(request):
    configuration = _configuration(request.user)
    period = request.GET.get("period", "24h")
    period_durations = {
        "1h": timedelta(hours=1),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    if period not in period_durations:
        return HttpResponseBadRequest("Choose a supported period: 1h, 24h, 7d, or 30d.")

    reading_query = SensorData.objects.filter(
        user=request.user,
        recorded_at__gte=timezone.now() - period_durations[period],
    ).order_by("-recorded_at")
    if request.GET.get("format") == "csv":
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="soilsense-readings.csv"'
        writer = csv.writer(response)
        writer.writerow(["Recorded at", "Temperature (C)", "Humidity (%)", "Moisture (%)"])
        for reading in reading_query.iterator():
            writer.writerow(
                [
                    reading.recorded_at.isoformat(),
                    reading.temperature,
                    reading.humidity,
                    reading.moisture,
                ]
            )
        return response

    readings = list(reading_query[:500])
    readings.reverse()
    latest = SensorData.objects.filter(user=request.user).first()
    return JsonResponse(
        {
            "connected": serial_monitor_for(request.user.pk).status()["connected"],
            "port": configuration.port,
            "error": serial_monitor_for(request.user.pk).status()["error"],
            "period": period,
            "latest": _serialize_reading(latest),
            "readings": [_serialize_reading(reading) for reading in readings],
        }
    )


def _serialize_reading(reading):
    if reading is None:
        return None
    return {
        "temperature": reading.temperature,
        "humidity": reading.humidity,
        "moisture": reading.moisture,
        "recorded_at": reading.recorded_at.isoformat(),
    }


@csrf_exempt
@require_POST
def ingest_api(request):
    try:
        key = uuid.UUID(request.headers.get("X-Api-Key", ""))
    except ValueError:
        return JsonResponse({"error": "invalid key"}, status=401)
    configuration = SerialConfiguration.objects.filter(ingest_key=key).first()
    if configuration is None or configuration.user_id is None:
        return JsonResponse({"error": "invalid key"}, status=401)
    try:
        data = json.loads(request.body)
        reading = SerialMonitor._parse_reading(json.dumps(data))
    except (ValueError, TypeError):
        reading = None
    if reading is None:
        return JsonResponse({"error": "invalid reading"}, status=400)
    SensorData.objects.create(
        user_id=configuration.user_id,
        temperature=reading[0], humidity=reading[1], moisture=reading[2],
    )
    return JsonResponse({"ok": True}, status=201)
