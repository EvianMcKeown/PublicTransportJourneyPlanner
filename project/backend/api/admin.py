from django.contrib import admin
from .models import (
    UserProfile,
    SavedRoute,
    Stop,
    Route,
    Trip,
    StopTime,
    Agency,
    Calendar,
    CalendarDate,
)


# ----------------------------
# User-related models
# ----------------------------

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "preference_min_walking", "preference_min_stops")
    search_fields = ("user__username",)


@admin.register(SavedRoute)
class SavedRouteAdmin(admin.ModelAdmin):
    list_display = ("user", "start_location", "end_location", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "start_location", "end_location")


# ----------------------------
# GTFS models
# ----------------------------

@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ("agency_id", "name", "url", "timezone")
    search_fields = ("agency_id", "name")


@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_display = (
        "service_id",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "start_date",
        "end_date",
    )
    search_fields = ("service_id",)


@admin.register(CalendarDate)
class CalendarDateAdmin(admin.ModelAdmin):
    list_display = ("service", "date", "exception_type")
    list_filter = ("exception_type", "date")
    search_fields = ("service__service_id",)


# ----------------------------
# Transport models
# ----------------------------

@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ("stop_id", "name", "lat", "lon")
    search_fields = ("stop_id", "name")


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("route_id", "short_name", "long_name", "agency")
    search_fields = ("route_id", "short_name", "long_name")


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("trip_id", "route", "service", "headsign", "direction_id")
    list_filter = ("route", "service", "direction_id")
    search_fields = ("trip_id", "headsign")


@admin.register(StopTime)
class StopTimeAdmin(admin.ModelAdmin):
    list_display = ("trip", "stop", "stop_sequence", "arrival_time", "departure_time")
    list_filter = ("trip", "stop")
    ordering = ("trip", "stop_sequence")
