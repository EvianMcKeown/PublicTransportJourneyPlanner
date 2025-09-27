from rest_framework import serializers
from .models import SavedRoute, UserProfile

class SavedRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedRoute
        fields = ["id", "start_location", "end_location", "created_at"]
