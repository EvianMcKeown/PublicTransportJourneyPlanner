from rest_framework import serializers
from rest_framework.fields import CharField
from rest_framework.serializers import FloatField, IntegerField
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
        fields = "__all__"  # you can list fields explicitly if you want control


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


class PlanRequestSerializer(serializers.Serializer):
    source_lat = FloatField(required=True)
    source_lon = FloatField(required=True)
    target_lat = FloatField(required=True)
    target_lon = FloatField(required=True)
    day = IntegerField(required=True)
    time = CharField(required=True)
    max_rounds = IntegerField(required=False, default=5)
    departure_minutes = IntegerField(required=False)
    debug = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if "departure_minutes" not in attrs and (
            "day" not in attrs or "time" not in attrs
        ):
            raise serializers.ValidationError(
                "Provide either departure_minutes or both day and time (HH:MM)."
            )
        return attrs
