from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, permissions, generics, status
from rest_framework.serializers import (
    ModelSerializer,
    Serializer,
    CharField,
    ValidationError,
)
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from typing import Any, Dict, Tuple
from rest_framework.views import APIView
from .raptor_engine import get_engine, to_mins
from .serializers import PlanRequestSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
import math
from algorithm_prototype.raptor import helper_functions as hf

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
from .serializers import (
    SavedRouteSerializer,
    UserProfileSerializer,
    StopSerializer,
    RouteSerializer,
    TripSerializer,
    StopTimeSerializer,
    AgencySerializer,
    CalendarSerializer,
    CalendarDateSerializer,
)


def closest_stop(lat, lon, stops) -> Tuple[str, float]:
    """
    Find the closest stop to (lat, lon) using a divide and conquer closest pair algorithm.
    stops: dict of {stop_id: Stop} where Stop has .lat and .lon
    Returns: stop_id, distance_m
    """
    # Convert stops to points
    points = [(sid, stop.lat, stop.lon) for sid, stop in stops.items()]

    # Sort by latitude
    points_sorted = sorted(points, key=lambda x: x[1])

    # Recursive closest pair (1D for latitude, brute force for small n)
    def closest_pair(points):
        n = len(points)
        if n <= 3:
            # Brute force
            min_dist = float("inf")
            min_sid = None
            for sid, plat, plon in points:
                d = hf.haversine(lat, lon, plat, plon)
                if d < min_dist:
                    min_dist = d
                    min_sid = sid
            return min_sid, min_dist
        mid = n // 2
        left = points[:mid]
        right = points[mid:]
        sid_l, dist_l = closest_pair(left)
        sid_r, dist_r = closest_pair(right)
        # Take closer of left/right
        if dist_l < dist_r:
            return sid_l, dist_l
        else:
            return sid_r, dist_r

    return closest_pair(points_sorted)


# -------------------------------
# AUTH
# -------------------------------
@api_view(["POST"])
def signup(request):
    username = request.data.get("username")
    password = request.data.get("password")

    if User.objects.filter(username=username).exists():
        return Response({"error": "User already exists"}, status=400)

    User.objects.create_user(username=username, password=password)
    return Response({"message": "User created"}, status=201)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["is_superuser"] = user.is_superuser
        token["is_staff"] = user.is_staff
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["username"] = self.user.username
        data["is_superuser"] = self.user.is_superuser
        data["is_staff"] = self.user.is_staff
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# -------------------------------
# ROUTE
# -------------------------------
@method_decorator(csrf_exempt, name="dispatch")
class PlanJourneyView(APIView):
    def post(self, request, *args, **kwargs):
        ser = PlanRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data: Dict[str, Any] = ser.validated_data

        engine = get_engine()

        source_lat_p = float(data["source_lat"])
        source_lon_p = float(data["source_lon"])
        target_lat_p = float(data["target_lat"])
        target_lon_p = float(data["target_lon"])

        # need to find closest stops to given lat/lon
        # source_id = data["source_id"].strip()
        # target_id = data["target_id"].strip()
        # if "source_lat" in data and "source_lon" in data:
        #    source_id, _ = closest_stop(
        #        data["source_lat"], data["source_lon"], engine.stops
        #    )
        # else:
        #    source_id = data["source_id"].strip()
        # if "target_lat" in data and "target_lon" in data:
        #    target_id, _ = closest_stop(
        #        data["target_lat"], data["target_lon"], engine.stops
        #    )
        # else:
        #    target_id = data["target_id"].strip()

        if "departure_minutes" in data:
            dep_mins = int(data["departure_minutes"])
        else:
            dep_mins = to_mins(int(data["day"]), data["time"])

        out = engine.plan(
            source_lat=source_lat_p,  # Pass as float, not string
            source_lon=source_lon_p,
            target_lat=target_lat_p,
            target_lon=target_lon_p,
            departure_minutes=dep_mins,
            max_rounds=data.get("max_rounds", 5),
            debug=False,
        )

        # Minimal response
        target_id = out.get("target_stop", {}).get("id")
        return Response(
            {
                "earliest_arrival": out.get("earliest_arrival"),
                "path": out["path"],  # ID-based steps
                "path_objs": out["path_objs"],  # JSON-safe enriched steps
                "source_stop": out.get(
                    "source_stop"
                ),  # Include stop info for debugging
                "target_stop": out.get("target_stop"),
            },
            status=status.HTTP_200_OK,
        )


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def get_route(request):
#    start = request.data.get("start_location")
#    end = request.data.get("end_location")
#
#    return Response(
#        {
#            "message": "Route generated successfully!",
#            "start": start,
#            "end": end,
#            "path": ["Stop A", "Stop B", "Stop C"],  # placeholder
#            "duration": "25 minutes",
#        }
#    )


# -------------------------------
# USER PREFERENCES
# -------------------------------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_preferences(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    profile.preference_min_walking = request.data.get("minWalking", False)
    profile.preference_min_stops = request.data.get("minStops", False)
    profile.save()

    return Response({"message": "Preferences updated successfully!"})


# -------------------------------
# SAVED ROUTES
# -------------------------------
class SavedRouteViewSet(viewsets.ModelViewSet):
    serializer_class = SavedRouteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedRoute.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# -------------------------------
# USER ACCOUNT
# -------------------------------
class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]


class UserDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordSerializer(Serializer):
    old_password = CharField(required=True)
    new_password = CharField(required=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise ValidationError("Old password is not correct")
        return value


class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response(
            {"message": "Password updated successfully"}, status=status.HTTP_200_OK
        )


# -------------------------------
# TRANSPORT DATA (Stops, Routes, Trips, StopTimes, Agency, Calendar, CalendarDate)
# -------------------------------
class StopViewSet(viewsets.ModelViewSet):
    queryset = Stop.objects.all()
    serializer_class = StopSerializer
    permission_classes = [permissions.AllowAny]  # open for now


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    permission_classes = [permissions.AllowAny]


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [permissions.AllowAny]


class StopTimeViewSet(viewsets.ModelViewSet):
    queryset = StopTime.objects.all()
    serializer_class = StopTimeSerializer
    permission_classes = [permissions.AllowAny]


class AgencyViewSet(viewsets.ModelViewSet):
    queryset = Agency.objects.all()
    serializer_class = AgencySerializer
    permission_classes = [permissions.AllowAny]


class CalendarViewSet(viewsets.ModelViewSet):
    queryset = Calendar.objects.all()
    serializer_class = CalendarSerializer
    permission_classes = [permissions.AllowAny]


class CalendarDateViewSet(viewsets.ModelViewSet):
    queryset = CalendarDate.objects.all()
    serializer_class = CalendarDateSerializer
    permission_classes = [permissions.AllowAny]
