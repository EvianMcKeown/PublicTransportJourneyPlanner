from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserPreferences, RoutePreferences, Route, RouteSegment

# Register the custom User model with the admin site
admin.site.register(User, UserAdmin)
admin.site.register(UserPreferences)
admin.site.register(RoutePreferences)
admin.site.register(Route)
admin.site.register(RouteSegment)
admin.site.site_header = "Journey Planner Admin"
admin.site.site_title = "Journey Planner Admin Portal"
