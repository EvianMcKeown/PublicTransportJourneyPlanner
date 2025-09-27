from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    signup,
    get_route,
    update_preferences,
    CustomTokenObtainPairView,
    SavedRouteViewSet,
    UserDetailView,          
    ChangePasswordView,      
)

# Router for SavedRouteViewSet
router = DefaultRouter()
router.register(r"routes", SavedRouteViewSet, basename="savedroute")

urlpatterns = [
    # Auth
    path("signup/", signup, name="signup"),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),

    # User account
    path("user/", UserDetailView.as_view(), name="user-detail"),
    path("user/change_password/", ChangePasswordView.as_view(), name="change-password"),

    # Routes & Preferences
    path("route/", get_route, name="get_route"),
    path("preferences/", update_preferences, name="update_preferences"),

    # Saved routes API
    path("", include(router.urls)),
]
