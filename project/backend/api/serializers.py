from rest_framework import serializers
from .models import (
    SavedRoute,
    UserProfile,
    Stop,
    Route,
    Trip,
    StopTime,
    Agency,
    Calendar,
    CalendarDate,
)


class SavedRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedRoute
        fields = ["id", "start_location", "end_location", "created_at"]


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = "__all__"   # you can list fields explicitly if you want control


class AgencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Agency
        fields = "__all__"


class CalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendar
        fields = "__all__"


class CalendarDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarDate
        fields = "__all__"


class StopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stop
        fields = "__all__"


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = "__all__"


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = "__all__"


class StopTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StopTime
        fields = "__all__"
