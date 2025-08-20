from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser

# Here we define classes to be used by the planner app.
# We will mirror our class diagram from Stage 2.

class User(AbstractUser):
    # Custom user model extending Django's AbstractUser
    pass

# Preferences model to store user preferences
class UserPreferences(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    allow_trains = models.BooleanField(blank=True, null=True)
    allow_busses = models.BooleanField(blank=True, null=True)
    allow_taxis = models.BooleanField(blank=True, null=True)
    max_walk_distance = models.IntegerField(verbose_name="Maximum Walk Distance (meters)", default=5000)
    
    def __str__(self):
        return f"{self.user.username}'s Preferences"

class RoutePreferences(models.Model):
    routeId = models.OneToOneField('Route', on_delete=models.CASCADE, related_name='route_preferences')
    allow_trains = models.BooleanField(blank=True, null=True)
    allow_busses = models.BooleanField(blank=True, null=True)
    allow_taxis = models.BooleanField(blank=True, null=True)
    max_walk_distance = models.IntegerField(verbose_name="Maximum Walk Distance (meters)", default=5000)

    def __str__(self):
        return f"Preferences for Route {self.routeId.routeId} - User: {self.routeId.user.username}"

class Route(models.Model):
    routeId = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_location = models.CharField(max_length=255)
    end_location = models.CharField(max_length=255)
    start_date_time = models.DateTimeField()

    def __str__(self):
        return f"Route from {self.start_location} to {self.end_location} starting on {self.date}"
    
class RouteSegment(models.Model):
    route = models.ForeignKey(Route, related_name='segments', on_delete=models.CASCADE)
    segment_type = models.CharField(max_length=50)  # e.g., 'walk', 'bus', 'train'
    start_location = models.CharField(max_length=255)
    end_location = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def __str__(self):
        return f"{self.segment_type.capitalize()} from {self.start_location} to {self.end_location}"
