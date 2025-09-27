from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, permissions, generics, status
from rest_framework.serializers import ModelSerializer, Serializer, CharField, ValidationError

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import UserProfile, SavedRoute
from .serializers import SavedRouteSerializer




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


# ROUTE 

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_route(request):
    start = request.data.get("start_location")
    end = request.data.get("end_location")

    return Response({
        "message": "Route generated successfully!",
        "start": start,
        "end": end,
        "path": ["Stop A", "Stop B", "Stop C"],
        "duration": "25 minutes"
    })


# USER PREFERENCES

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_preferences(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    profile.preference_min_walking = request.data.get("minWalking", False)
    profile.preference_min_stops = request.data.get("minStops", False)
    profile.save()

    return Response({"message": "Preferences updated successfully!"})


# SAVED ROUTES

class SavedRouteViewSet(viewsets.ModelViewSet):
    serializer_class = SavedRouteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        
        return SavedRoute.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        
        serializer.save(user=self.request.user)


# USER ACCOUNT

# Serializer for user profile updates
class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]


class UserDetailView(generics.RetrieveUpdateAPIView):
   
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# Password change
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
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"message": "Password updated successfully"}, status=status.HTTP_200_OK)
