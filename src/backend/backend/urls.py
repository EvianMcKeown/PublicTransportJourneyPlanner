from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django admin panel superuser login
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]
