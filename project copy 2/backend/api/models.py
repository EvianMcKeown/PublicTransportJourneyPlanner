from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preference_min_walking = models.BooleanField(default=False)
    preference_min_stops = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


class SavedRoute(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="saved_routes"   
    )
    start_location = models.CharField(max_length=255)
    end_location = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # newest routes first

    def __str__(self):
        return f"{self.user.username}: {self.start_location} → {self.end_location}"
